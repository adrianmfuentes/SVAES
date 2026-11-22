from __future__ import annotations

from bootstrap.repositories import get_custom_role_repository, get_organization_repository, get_user_membership_repository, get_user_repository
from functools import lru_cache

from fastapi import Depends
from features.identity.application.ports.i_access_request_repository import IAccessRequestRepository
from features.identity.application.ports.i_auth_service import IAuthService
from features.identity.application.ports.i_custom_role_service import ICustomRoleService
from features.identity.application.ports.i_password_hasher import IPasswordHasher
from features.identity.application.ports.i_user_service import IUserService
from features.identity.application.use_cases.account_recovery import ActivateAccount, RequestPasswordReset, ResetPassword
from features.identity.application.use_cases.auth_service import AuthService
from features.identity.application.use_cases.create_access_request import CreateAccessRequest
from features.identity.application.use_cases.custom_role_service import CustomRoleService
from features.identity.application.use_cases.user_service import UserService
from features.identity.infrastructure.gateways.jwt_handler import JwtHandler
from features.identity.infrastructure.gateways.password_hasher import BcryptPasswordHasher
from features.identity.infrastructure.gateways.totp import PyotpTotpService
from features.identity.infrastructure.gateways.totp import SvgQrRenderer
from features.identity.infrastructure.persistence.access_request_repository import SqlAccessRequestRepository
from features.identity.infrastructure.persistence.custom_role_repository import SqlCustomRoleRepository
from features.identity.infrastructure.persistence.user_membership_repository import SqlUserMembershipRepository
from features.identity.infrastructure.persistence.user_repository import SqlUserRepository
from features.organizations.container import _transactional_organization_service
from features.organizations.infrastructure.persistence.organization_repository import SqlOrganizationRepository
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.config import Settings
from shared.infrastructure.config import get_settings
from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from shared.infrastructure.smtp_mailer import email_service
from shared.infrastructure.sql_unit_of_work import SqlUnitOfWork
from shared.infrastructure.system_clock import SystemClock


def get_settings_dependency() -> Settings:
    return get_settings()


def get_jwt_handler(
    settings: Settings = Depends(get_settings_dependency),
) -> JwtHandler:
    return _jwt_for_configuration(
        settings.jwt_secret_key, settings.jwt_algorithm, settings.jwt_expire_minutes, settings.redis_url,
    )


@lru_cache(maxsize=1)
def _jwt_for_configuration(secret: str, algorithm: str, expiry_minutes: int, redis_url: str | None) -> JwtHandler:
    return JwtHandler(
        secret=secret,
        algorithm=algorithm,
        access_token_expire_minutes=expiry_minutes,
        refresh_token_expire_days=30,
        redis_url=redis_url,
    )


def close_jwt_handler(settings: Settings) -> None:
    get_jwt_handler(settings).close()
    _jwt_for_configuration.cache_clear()



def get_password_hasher() -> IPasswordHasher:
    return BcryptPasswordHasher()


def get_auth_service(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings_dependency),
) -> IAuthService:
    jwt_handler = get_jwt_handler(settings)
    password_hasher = get_password_hasher()
    return AuthService(
        user_repository=user_repo,
        token_service=jwt_handler,
        password_hasher=password_hasher,
        audit_logger=get_audit_logger(),
        totp_service=PyotpTotpService(),
        qr_renderer=SvgQrRenderer(),
    )


def get_create_access_request() -> CreateAccessRequest:
    unit_of_work = SqlUnitOfWork(AsyncSessionLocal())
    return CreateAccessRequest(
        requests=SqlAccessRequestRepository(unit_of_work.session),
        users=SqlUserRepository(unit_of_work.session),
        organizations=_transactional_organization_service(unit_of_work),
        password_hasher=get_password_hasher(),
        mailer=email_service,
        clock=SystemClock(),
        unit_of_work=unit_of_work,
    )


def get_user_service(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    membership_repo: SqlUserMembershipRepository = Depends(get_user_membership_repository),
) -> IUserService:
    password_hasher = get_password_hasher()
    return UserService(
        user_repository=user_repo,
        organization_repository=org_repo,
        password_hasher=password_hasher,
        user_membership_repository=membership_repo,
        audit_logger=get_audit_logger(),
    )


def get_custom_role_service(
    role_repo: SqlCustomRoleRepository = Depends(get_custom_role_repository),
) -> ICustomRoleService:
    return CustomRoleService(custom_role_repository=role_repo, audit_logger=get_audit_logger())


def get_activate_account() -> ActivateAccount:
    return ActivateAccount(get_user_repository(), get_password_hasher(), SystemClock())


def get_password_reset_request() -> RequestPasswordReset:
    return RequestPasswordReset(get_user_repository(), email_service, SystemClock())


def get_reset_password() -> ResetPassword:
    return ResetPassword(get_user_repository(), get_password_hasher(), SystemClock())


def get_access_request_repository() -> IAccessRequestRepository:
    return SqlAccessRequestRepository()
