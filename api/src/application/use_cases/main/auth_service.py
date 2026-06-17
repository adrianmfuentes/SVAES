import asyncio
import io
import base64
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID
from application.ports.input.i_auth_service import IAuthService, AuthTokens, LoginResult, TotpSetupResult
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_token_service import ITokenService
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
    ) -> LoginResult:
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

        password_ok = await asyncio.to_thread(
            self._password_hasher.verify_password, password, user.hashed_password
        )
        if not password_ok:
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

        needs_update = user.failed_login_attempts > 0 or user.locked_until is not None
        if self._password_hasher.needs_rehash(user.hashed_password):
            user.hashed_password = await asyncio.to_thread(
                self._password_hasher.hash_password, password
            )
            needs_update = True
        if needs_update:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self._user_repo.update(user)

        if user.totp_enabled:
            totp_token = self._token_service.create_totp_pending_token(user.id)
            return LoginResult(requires_2fa=True, totp_token=totp_token)

        return self._issue_tokens(user)

    async def verify_totp(self, totp_token: str, code: str) -> LoginResult:
        import pyotp  # noqa: PLC0415

        user_id = self._token_service.verify_totp_pending_token(totp_token)
        if not user_id:
            raise ValidationError("Token 2FA inválido o expirado")

        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.totp_enabled or not user.totp_secret:
            raise ValidationError("Autenticación 2FA fallida")

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            user.failed_login_attempts = user.failed_login_attempts + 1
            await self._user_repo.update(user)
            audit = get_audit_logger()
            audit.log(AuditEntry(
                event=AuditEvent.LOGIN_FAILED,
                user_id=user.id,
                organization_id=user.organization_id,
                resource_type="user",
                resource_id=user.id,
                details={"reason": "invalid_totp_code"},
            ))
            raise ValidationError("Código 2FA inválido")

        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            await self._user_repo.update(user)

        return self._issue_tokens(user)

    async def setup_totp(self, user_id: UUID) -> TotpSetupResult:
        import pyotp  # noqa: PLC0415
        import segno  # noqa: PLC0415

        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("Usuario no encontrado")

        secret = user.totp_secret if (user.totp_secret and not user.totp_enabled) else pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="SVAES")

        buf = io.BytesIO()
        segno.make_qr(uri).save(buf, kind="svg", scale=4, border=1)
        qr_data_url = "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()

        user.totp_secret = secret
        await self._user_repo.update(user)

        return TotpSetupResult(totp_uri=uri, secret=secret, qr_data_url=qr_data_url)

    async def enable_totp(self, user_id: UUID, code: str) -> None:
        import pyotp  # noqa: PLC0415

        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.totp_secret:
            raise ValidationError("Inicia la configuración 2FA primero")

        if user.totp_enabled:
            raise ValidationError("El 2FA ya está activado")

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise ValidationError("Código inválido. Verifica que tu aplicación esté sincronizada.")

        user.totp_enabled = True
        await self._user_repo.update(user)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.TOTP_ENABLED,
            user_id=user.id,
            organization_id=user.organization_id,
            resource_type="user",
            resource_id=user.id,
        ))

    async def disable_totp(self, user_id: UUID, code: str) -> None:
        import pyotp  # noqa: PLC0415

        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.totp_enabled or not user.totp_secret:
            raise ValidationError("El 2FA no está activado")

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise ValidationError("Código inválido")

        user.totp_enabled = False
        user.totp_secret = None
        await self._user_repo.update(user)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.TOTP_DISABLED,
            user_id=user.id,
            organization_id=user.organization_id,
            resource_type="user",
            resource_id=user.id,
        ))

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

    def _issue_tokens(self, user: User) -> LoginResult:
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
        return LoginResult(tokens=tokens, user_id=user.id, role=user.role.value)
