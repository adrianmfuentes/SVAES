import asyncio
import logging
from typing import List
from uuid import UUID

from features.identity.application.ports.i_password_hasher import IPasswordHasher
from features.identity.application.ports.i_user_membership_repository import IUserMembershipRepository
from features.identity.application.ports.i_user_repository import IUserRepository
from features.identity.domain.user import User
from features.organizations.application.ports.i_organization_repository import IOrganizationRepository
from shared.application.i_audit_logger import IAuditLogger
from shared.domain.audit import AuditEntry, AuditEvent
from shared.domain.enums import UserRole
from shared.domain.exceptions import AuthenticationError, EntityNotFoundError, ValidationError


_log = logging.getLogger(__name__)


class DeleteUserAccount:
    def __init__(
        self, *, users: IUserRepository, organizations: IOrganizationRepository,
        memberships: IUserMembershipRepository | None, passwords: IPasswordHasher, audit: IAuditLogger,
    ) -> None:
        self._user_repo = users
        self._org_repo = organizations
        self._membership_repo = memberships
        self._password_hasher = passwords
        self._audit_logger = audit

    async def execute(self, user_id: UUID, requested_by: UUID, password: str) -> None:
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

        self._audit_logger.log(AuditEntry(
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
