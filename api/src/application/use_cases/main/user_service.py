import asyncio
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
from application.ports.input.i_user_service import IUserService
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_organization_repository import IOrganizationRepository
from application.ports.output.i_user_membership_repository import IUserMembershipRepository
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.entities.user import User, UserMembership
from domain.enums import UserRole
from domain.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError, AuthenticationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)

class UserService(IUserService):
    def __init__(
        self,
        user_repository: IUserRepository,
        organization_repository: IOrganizationRepository,
        password_hasher: IPasswordHasher,
        user_membership_repository: Optional[IUserMembershipRepository] = None,
    ) -> None:
        self._user_repo = user_repository
        self._org_repo = organization_repository
        self._password_hasher = password_hasher
        self._membership_repo = user_membership_repository


    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self._user_repo.get_by_id(user_id)


    async def update_profile(self, user_id: UUID, display_name: Optional[str] = None) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        if display_name:
            user.display_name = display_name

        return await self._user_repo.update(user)


    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        if not await asyncio.to_thread(self._password_hasher.verify_password, current_password, user.hashed_password):
            return False

        user.hashed_password = await asyncio.to_thread(self._password_hasher.hash_password, new_password)
        # Invalida todos los access/refresh tokens emitidos antes del cambio de
        # contraseña (otros dispositivos, un token filtrado, etc.), no solo la
        # sesión actual - ver comprobación de `token_version` en get_current_user.
        user.token_version += 1
        await self._user_repo.update(user)
        return True


    async def list_organization_users(self, organization_id: UUID, skip: int = 0, limit: int = 50) -> List[User]:
        if not self._membership_repo:
            return await self._user_repo.list_all(organization_id=organization_id, skip=skip, limit=limit)

        memberships = await self._membership_repo.list_by_organization(organization_id, skip=skip, limit=limit)
        users: List[User] = []
        for membership in memberships:
            member = await self._user_repo.get_by_id(membership.user_id)
            if member:
                member.role = membership.role
                users.append(member)
        return users


    async def invite_user(self, organization_id: UUID, email: str, role: UserRole, requested_by: UUID) -> User:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        now = datetime.now(timezone.utc)
        activation_token = str(uuid4())
        activation_token_expiry = now + timedelta(hours=24)

        existing = await self._user_repo.get_by_email(email)
        if existing:
            created = await self._invite_existing_user(
                existing, organization_id, role, activation_token, activation_token_expiry
            )
        else:
            created = await self._invite_new_user(
                email, organization_id, role, activation_token, activation_token_expiry
            )

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_INVITED,
            user_id=requested_by,
            organization_id=organization_id,
            resource_type="user",
            resource_id=created.id,
            details={"email": email, "role": role.value},
        ))
        _log.info("User invited: by=%s org=%s role=%s", requested_by, organization_id, role.value)

        return created

    async def _invite_existing_user(
        self,
        existing: User,
        organization_id: UUID,
        role: UserRole,
        activation_token: str,
        activation_token_expiry: datetime,
    ) -> User:
        if not self._membership_repo:
            if existing.organization_id is not None:
                raise DuplicateEntityError(f"El usuario {existing.email} ya pertenece a una organización")
            existing.organization_id = organization_id
            existing.role = role
            existing.activation_token = activation_token
            existing.activation_token_expiry = activation_token_expiry
            existing.is_active = False
            return await self._user_repo.update(existing)

        already_member = await self._membership_repo.get(existing.id, organization_id)
        if already_member:
            raise DuplicateEntityError(f"El usuario {existing.email} ya pertenece a esta organización")
        await self._membership_repo.create(UserMembership(
            id=uuid4(), user_id=existing.id, organization_id=organization_id, role=role,
        ))
        if existing.organization_id is not None:
            existing.role = role
            return existing

        existing.organization_id = organization_id
        existing.role = role
        existing.activation_token = activation_token
        existing.activation_token_expiry = activation_token_expiry
        existing.is_active = False
        return await self._user_repo.update(existing)

    async def _invite_new_user(
        self,
        email: str,
        organization_id: UUID,
        role: UserRole,
        activation_token: str,
        activation_token_expiry: datetime,
    ) -> User:
        temp_password = await asyncio.to_thread(self._password_hasher.hash_password, str(uuid4())[:8])
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=temp_password,
            display_name=email.split("@")[0],
            role=role,
            organization_ids=[organization_id],
            is_active=False,
            activation_token=activation_token,
            activation_token_expiry=activation_token_expiry,
        )
        created = await self._user_repo.create(user)
        if self._membership_repo:
            await self._membership_repo.create(UserMembership(
                id=uuid4(), user_id=created.id, organization_id=organization_id, role=role,
            ))
        return created


    async def update_user_role(self, user_id: UUID, organization_id: UUID, new_role: UserRole, requested_by: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")

        if self._membership_repo:
            membership = await self._membership_repo.get(user_id, organization_id)
            if not membership:
                raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")
            old_role = membership.role
        else:
            if user.organization_id != organization_id:
                raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")
            old_role = user.role

        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        if org.owner_id == user_id:
            raise ValidationError("No se puede cambiar el rol del Owner de la organización")

        if self._membership_repo:
            await self._membership_repo.update_role(user_id, organization_id, new_role)
            if user.organization_id == organization_id:
                user.role = new_role
                updated = await self._user_repo.update(user)
            else:
                # organization_id is not the user's active org: the change only
                # affects their membership row there, not the in-memory/DB user,
                # whose .role reflects their active org. Return a detached copy
                # so the response shows the role just granted without mutating
                # the shared `user` object (its active role must stay intact).
                updated = replace(user, role=new_role)
        else:
            user.role = new_role
            updated = await self._user_repo.update(user)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_ROLE_CHANGED,
            user_id=requested_by,
            organization_id=organization_id,
            resource_type="user",
            resource_id=user_id,
            details={"target_user": str(user_id), "old_role": old_role.value, "new_role": new_role.value},
        ))
        _log.info("User role changed: by=%s user=%s org=%s %s->%s", requested_by, user_id, organization_id, old_role.value, new_role.value)

        return updated


    async def remove_user_from_organization(self, user_id: UUID, organization_id: UUID, requested_by: UUID) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")

        if self._membership_repo:
            membership = await self._membership_repo.get(user_id, organization_id)
            if not membership:
                raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")
        elif user.organization_id != organization_id:
            raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")

        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        if org.owner_id == user_id:
            raise ValidationError("No se puede eliminar al Owner de la organización")

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_REMOVED,
            user_id=requested_by,
            organization_id=organization_id,
            resource_type="user",
            resource_id=user_id,
            details={"removed_user": str(user_id), "email": user.email},
        ))
        _log.info("User removed from org: by=%s user=%s org=%s", requested_by, user_id, organization_id)

        if self._membership_repo:
            await self._membership_repo.delete(user_id, organization_id)

        if user.organization_id == organization_id:
            remaining = await self._membership_repo.list_by_user(user_id) if self._membership_repo else []
            if remaining:
                fallback = remaining[0]
                user.organization_id = fallback.organization_id
                user.role = fallback.role
            else:
                user.organization_id = None
                user.role = UserRole.U2
            await self._user_repo.update(user)

    async def create_user(
        self,
        email: str,
        display_name: str,
        password: str,
        role: UserRole,
        terms_accepted_at=None,
        privacy_accepted_at=None,
    ) -> User:
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise DuplicateEntityError(f"Ya existe un usuario con email: {email}")

        hashed = await asyncio.to_thread(self._password_hasher.hash_password, password)
        user = User(
            id=uuid4(),
            email=email,
            display_name=display_name,
            hashed_password=hashed,
            role=role,
            is_active=True,
            terms_accepted_at=terms_accepted_at,
            privacy_accepted_at=privacy_accepted_at,
        )
        created = await self._user_repo.create(user)
        _log.info("User created: email=%s role=%s", email, role.value)
        return created

    async def activate_user(self, user_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        user.is_active = True
        updated = await self._user_repo.update(user)
        _log.info("User activated: id=%s", user_id)
        return updated

    async def deactivate_user(self, user_id: UUID, requested_by: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        user.is_active = False
        updated = await self._user_repo.update(user)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_DEACTIVATED,
            user_id=requested_by,
            organization_id=None,
            resource_type="user",
            resource_id=user_id,
            details={"email": user.email},
        ))
        _log.info("User deactivated: by=%s user=%s", requested_by, user_id)
        return updated

    async def update_global_role(self, user_id: UUID, new_role: UserRole, requested_by: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        old_role = user.role
        user.role = new_role
        updated = await self._user_repo.update(user)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_ROLE_CHANGED,
            user_id=requested_by,
            organization_id=None,
            resource_type="user",
            resource_id=user_id,
            details={"target_user": str(user_id), "old_role": old_role.value, "new_role": new_role.value},
        ))
        _log.info("Global role changed: by=%s user=%s %s->%s", requested_by, user_id, old_role.value, new_role.value)
        return updated

    async def list_all_users(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: Optional[bool] = None,
        role: Optional[UserRole] = None,
    ) -> List[User]:
        active_only = True if is_active is None else is_active
        users = await self._user_repo.list_all(
            organization_id=None,
            active_only=active_only,
            skip=skip,
            limit=limit,
        )
        if role is not None:
            users = [u for u in users if u.role == role]
        return users

    async def delete_user_account(self, user_id: UUID, requested_by: UUID, password: str) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        if user.role == UserRole.U3:
            raise ValidationError("Los administradores globales no pueden eliminar su cuenta")

        if not await asyncio.to_thread(self._password_hasher.verify_password, password, user.hashed_password):
            raise AuthenticationError("Contraseña incorrecta")

        org_ids = await self._resolve_user_organization_ids(user)
        if org_ids:
            await self._release_owned_organizations(org_ids, user_id)
            if self._membership_repo:
                await self._membership_repo.delete_all_for_user(user_id)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_ACCOUNT_DELETED,
            user_id=requested_by,
            organization_id=None,
            resource_type="user",
            resource_id=user_id,
            details={"deleted_email": user.email},
        ))
        _log.info("User account deleted: by=%s user=%s", requested_by, user_id)

        await self._user_repo.delete(user_id)

    async def _resolve_user_organization_ids(self, user: User) -> List[UUID]:
        if not self._membership_repo:
            return user.organization_ids
        memberships = await self._membership_repo.list_by_user(user.id)
        return [m.organization_id for m in memberships]

    async def _release_owned_organizations(self, org_ids: List[UUID], user_id: UUID) -> None:
        for org_id in org_ids:
            org = await self._org_repo.get_by_id(org_id)
            if not org or org.owner_id != user_id:
                continue

            members = await self._user_repo.list_all(organization_id=org_id, active_only=False, skip=0, limit=100)
            other_members = [m for m in members if m.id != user_id]
            if other_members:
                raise ValidationError("Debes transferir la propiedad de la organización antes de eliminar tu cuenta")

            await self._org_repo.delete(org_id)
            _log.info("Organization deleted before account deletion: org=%s", org_id)

    async def list_user_organizations(self, user_id: UUID) -> List[UserMembership]:
        if not self._membership_repo:
            return []
        return await self._membership_repo.list_by_user(user_id)

    async def switch_active_organization(self, user_id: UUID, organization_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        if not self._membership_repo:
            raise ValidationError("La función multi-organización no está disponible")

        membership = await self._membership_repo.get(user_id, organization_id)
        if not membership:
            raise ValidationError("No perteneces a esta organización")

        user.organization_id = organization_id
        user.role = membership.role
        updated = await self._user_repo.update(user)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_ORG_SWITCHED,
            user_id=user_id,
            organization_id=organization_id,
            resource_type="user",
            resource_id=user_id,
            details={"new_role": membership.role.value},
        ))
        _log.info("User switched active organization: user=%s org=%s role=%s", user_id, organization_id, membership.role.value)

        return updated