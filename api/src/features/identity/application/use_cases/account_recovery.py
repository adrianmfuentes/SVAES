import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from features.identity.application.ports.i_password_hasher import IPasswordHasher
from features.identity.application.ports.i_user_repository import IUserRepository
from shared.application.i_clock import IClock
from shared.application.i_mailer import IMailer
from shared.domain.exceptions import ValidationError


_log = logging.getLogger(__name__)


class AccountTokenExpired(ValidationError):
    pass


def _as_utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


class ActivateAccount:
    def __init__(self, users: IUserRepository, passwords: IPasswordHasher, clock: IClock):
        self._users = users
        self._passwords = passwords
        self._clock = clock

    async def execute(self, token: str, password: str) -> str:
        user = await self._users.get_by_activation_token(token)
        if not user:
            raise ValidationError("Token de activaci?n inv?lido.")
        expiry = _as_utc(user.activation_token_expiry)
        if expiry and expiry < self._clock.now():
            raise AccountTokenExpired("El token de activaci?n ha expirado.")

        user.hashed_password = await asyncio.to_thread(self._passwords.hash_password, password)
        user.is_active = True
        user.activation_token = None
        user.activation_token_expiry = None
        await self._users.update(user)
        return user.email


class RequestPasswordReset:
    def __init__(self, users: IUserRepository, mailer: IMailer, clock: IClock):
        self._users = users
        self._mailer = mailer
        self._clock = clock

    async def execute(self, email: str) -> None:
        try:
            user = await self._users.get_by_email(email)
            if user and user.is_active:
                token = secrets.token_urlsafe(32)
                user.password_reset_token = token
                user.password_reset_token_expiry = self._clock.now() + timedelta(hours=1)
                await self._users.update(user)
                await self._mailer.send_password_reset_email(user.email, user.display_name or user.email, token)
        except Exception:
            email_hash = hashlib.sha256(email.encode()).hexdigest()[:16]
            _log.exception("Forgot-password error for hash=%s", email_hash)


class ResetPassword:
    def __init__(self, users: IUserRepository, passwords: IPasswordHasher, clock: IClock):
        self._users = users
        self._passwords = passwords
        self._clock = clock

    async def execute(self, token: str, password: str) -> None:
        user = await self._users.get_by_password_reset_token(token)
        if not user:
            raise ValidationError("Token de restablecimiento inv?lido.")
        expiry = _as_utc(user.password_reset_token_expiry)
        if not expiry or expiry < self._clock.now():
            raise AccountTokenExpired("El token de restablecimiento ha expirado.")

        user.hashed_password = await asyncio.to_thread(self._passwords.hash_password, password)
        user.password_reset_token = None
        user.password_reset_token_expiry = None
        user.token_version += 1
        await self._users.update(user)
