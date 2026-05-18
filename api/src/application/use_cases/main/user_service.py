from typing import Optional, List
from uuid import UUID, uuid4
from application.ports.input.i_user_service import IUserService
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_organization_repository import IOrganizationRepository
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError, AuthenticationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)

"""
Este módulo define el servicio de usuario, que es responsable de gestionar los usuarios dentro del sistema. Incluye la lógica de negocio para obtener 
un usuario por ID, actualizar el perfil de un usuario, cambiar la contraseña, listar los usuarios de una organización, invitar a un nuevo usuario a 
una organización, actualizar el rol de un usuario dentro de una organización, y eliminar a un usuario de una organización.
"""
class UserService(IUserService):
    def __init__(
        self,
        user_repository: IUserRepository,
        organization_repository: IOrganizationRepository,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._user_repo = user_repository
        self._org_repo = organization_repository
        self._password_hasher = password_hasher


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

        if not self._password_hasher.verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = self._password_hasher.hash_password(new_password)
        await self._user_repo.update(user)
        return True


    async def list_organization_users(self, organization_id: UUID, skip: int = 0, limit: int = 50) -> List[User]:
        return await self._user_repo.list_all(organization_id=organization_id, skip=skip, limit=limit)


    async def invite_user(self, organization_id: UUID, email: str, role: UserRole, requested_by: UUID) -> User:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        existing = await self._user_repo.get_by_email(email)
        if existing:
            if existing.organization_id is not None:
                raise DuplicateEntityError(f"El usuario {email} ya pertenece a una organización")
            existing.organization_id = organization_id
            existing.role = role
            created = await self._user_repo.update(existing)
        else:
            temp_password = self._password_hasher.hash_password(str(uuid4())[:8])
            user = User(
                id=uuid4(),
                email=email,
                hashed_password=temp_password,
                display_name=email.split("@")[0],
                role=role,
                organization_ids=[organization_id],
                is_active=False,
            )
            created = await self._user_repo.create(user)

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


    async def update_user_role(self, user_id: UUID, organization_id: UUID, new_role: UserRole, requested_by: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user or user.organization_id != organization_id:
            raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")

        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        if org.owner_id == user_id:
            raise ValidationError("No se puede cambiar el rol del Owner de la organización")

        old_role = user.role
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
        if not user or user.organization_id != organization_id:
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

        user.organization_id = None
        user.role = UserRole.U1
        await self._user_repo.update(user)

    async def create_user(self, email: str, display_name: str, password: str, role: UserRole) -> User:
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise DuplicateEntityError(f"Ya existe un usuario con email: {email}")

        hashed = self._password_hasher.hash_password(password)
        user = User(
            id=uuid4(),
            email=email,
            display_name=display_name,
            hashed_password=hashed,
            role=role,
            is_active=True,
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

        if not self._password_hasher.verify_password(password, user.hashed_password):
            raise AuthenticationError("Contraseña incorrecta")

        if user.organization_ids:
            for org_id in user.organization_ids:
                org = await self._org_repo.get_by_id(org_id)
                if org and org.owner_id == user_id:
                    raise ValidationError("No puedes eliminar tu cuenta siendo propietario de una organización. Transfiere la propiedad primero.")

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