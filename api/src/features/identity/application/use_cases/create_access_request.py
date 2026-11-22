import asyncio
import logging
from datetime import timedelta
from uuid import uuid4

from features.organizations.application.ports.i_organization_service import IOrganizationService
from features.identity.application.ports.i_access_request_repository import IAccessRequestRepository
from features.identity.application.ports.i_password_hasher import IPasswordHasher
from features.identity.application.ports.i_user_repository import IUserRepository
from features.identity.domain.access_request import AccessRequest
from features.identity.domain.user import User
from shared.domain.enums import AccessRequestStatus, UserRole
from shared.domain.exceptions import DuplicateEntityError
from shared.application.i_clock import IClock
from shared.application.i_mailer import IMailer
from shared.application.i_unit_of_work import IUnitOfWork


_log = logging.getLogger(__name__)


class AccessRequestAlreadyExists(DuplicateEntityError):
    pass


class CreateAccessRequest:
    def __init__(
        self,
        requests: IAccessRequestRepository,
        users: IUserRepository,
        organizations: IOrganizationService,
        password_hasher: IPasswordHasher,
        mailer: IMailer,
        clock: IClock,
        unit_of_work: IUnitOfWork,
    ) -> None:
        self._requests = requests
        self._users = users
        self._organizations = organizations
        self._password_hasher = password_hasher
        self._mailer = mailer
        self._clock = clock
        self._unit_of_work = unit_of_work

    async def execute(
        self, requester_name: str, requester_email: str, organization_name: str,
        organization_description: str | None,
    ) -> AccessRequest:
        async with self._unit_of_work.transaction():
            if await self._requests.get_by_email(requester_email) or await self._users.get_by_email(requester_email):
                raise AccessRequestAlreadyExists("An account or pending request already exists for this email.")

            slug = organization_name.lower().strip().replace(" ", "-").replace("--", "-").strip("-")
            now = self._clock.now()
            activation_token = str(uuid4())
            password = await asyncio.to_thread(self._password_hasher.hash_password, str(uuid4()))
            user = await self._users.create(User(
                id=uuid4(), email=requester_email, display_name=requester_name,
                hashed_password=password, role=UserRole.U4, is_active=False,
                activation_token=activation_token, activation_token_expiry=now + timedelta(hours=24),
                created_at=now, updated_at=now,
            ))
            await self._organizations.create_organization(name=organization_name, slug=slug, owner_id=user.id)
            request = await self._requests.create(AccessRequest(
                requester_name=requester_name, requester_email=requester_email,
                organization_name=organization_name, organization_description=organization_description,
                slug_preview=slug, status=AccessRequestStatus.APPROVED, reviewed_at=now,
                created_at=now, updated_at=now,
            ))

        try:
            await self._mailer.send_activation_email(user.email, user.display_name, activation_token)
        except Exception:
            _log.warning("Activation email failed for new user")
        return request
