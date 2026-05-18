import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
from uuid import UUID
from application.ports.input.i_auth_service import IAuthService, AuthTokens
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_token_service import ITokenService, TokenPayload
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import ValidationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger

_log = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 10
LOCKOUT_DURATION_MINUTES = 15


class AuthService(IAuthService):
    def __init__(
        self,
        user_repository: IUserRepository,
        token_service: ITokenService,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._user_repo = user_repository
        self._token_service = token_service
        self._password_hasher = password_hasher

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Tuple[AuthTokens, UUID, UserRole]:
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise ValidationError("Credenciales inválidas")

        if not user.is_active:
            raise ValidationError("Usuario inactivo")

        now = datetime.now(timezone.utc)
        if user.locked_until and user.locked_until > now:
            remaining = (user.locked_until - now).seconds // 60
            raise ValidationError(f"Cuenta bloqueada. Intenta en {remaining} minutos.")

        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            user.failed_login_attempts = 0
            await self._user_repo.update(user)
            audit = get_audit_logger()
            audit.log(AuditEntry(
                event=AuditEvent.LOGIN_FAILED,
                user_id=user.id,
                organization_id=user.organization_id,
                resource_type="user",
                resource_id=user.id,
                details={"reason": "max_attempts_exceeded"},
            ))
            audit.log(AuditEntry(
                event=AuditEvent.SECURITY_BREACH_DETECTED,
                user_id=user.id,
                organization_id=user.organization_id,
                resource_type="user",
                resource_id=user.id,
                details={
                    "reason": "account_lockout",
                    "lockout_duration_minutes": LOCKOUT_DURATION_MINUTES,
                    "alert": "GDPR Art.33 — review if personal data breach occurred",
                },
            ))
            _log.warning("SECURITY ALERT: account locked out after max failed attempts — user_id=%s", user.id)
            raise ValidationError(f"Demasiados intentos fallidos. Cuenta bloqueada por {LOCKOUT_DURATION_MINUTES} minutos.")

        if not self._password_hasher.verify_password(password, user.hashed_password):
            user.failed_login_attempts = user.failed_login_attempts + 1
            await self._user_repo.update(user)
            audit = get_audit_logger()
            audit.log(AuditEntry(
                event=AuditEvent.LOGIN_FAILED,
                user_id=user.id,
                organization_id=user.organization_id,
                resource_type="user",
                resource_id=user.id,
                details={"reason": "invalid_password"},
            ))
            remaining = MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
            raise ValidationError(f"Credenciales inválidas. Intentos restantes: {remaining}")

        if user.failed_login_attempts > 0 or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self._user_repo.update(user)

        access_token = self._token_service.create_access_token(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            organization_id=user.organization_id,
            expires_in=3600,
        )
        refresh_token = self._token_service.create_refresh_token(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            organization_id=user.organization_id,
        )

        tokens = AuthTokens(access_token=access_token, refresh_token=refresh_token)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.LOGIN_SUCCESS,
            user_id=user.id,
            organization_id=user.organization_id,
            resource_type="user",
            resource_id=user.id,
        ))

        return tokens, user.id, user.role.value

    async def refresh_access_token(self, refresh_token: str) -> Optional[AuthTokens]:
        if not self._token_service.is_refresh_token(refresh_token):
            return None
        try:
            payload = self._token_service.decode_token(refresh_token)
        except ValueError:
            return None

        user = await self._user_repo.get_by_id(payload.user_id)
        if not user:
            return None

        access_token = self._token_service.create_access_token(
            user_id=payload.user_id,
            role=payload.role,
            email=payload.email,
            organization_id=user.organization_id,
            expires_in=3600,
        )
        new_refresh_token = self._token_service.create_refresh_token(
            user_id=payload.user_id,
            role=payload.role,
            email=payload.email,
            organization_id=user.organization_id,
        )

        return AuthTokens(access_token=access_token, refresh_token=new_refresh_token)

    async def logout(self, user_id: UUID, token: str) -> None:
        self._token_service.blacklist_token(token, 0)
        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.USER_LOGGED_OUT,
            user_id=user_id,
            organization_id=None,
            resource_type="user",
            resource_id=user_id,
        ))
        _log.info("User logged out: user=%s", user_id)
