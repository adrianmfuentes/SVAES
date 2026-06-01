import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
from infrastructure.secondary.database.models.user_model import UserModel
from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
from domain.enums import UserRole
from core.config import Settings

_log = logging.getLogger(__name__)


async def seed_admin_user(settings: Settings) -> None:
    hasher = BcryptPasswordHasher()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.role == UserRole.U3.value).limit(1)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin is not None:
            if existing_admin.organization_id is not None:
                existing_admin.organization_id = None
                await session.commit()
                _log.warning(
                    "Admin user (id=%s) had organization_id set — stripped to enforce invariant.",
                    existing_admin.id,
                )
            else:
                _log.info("Admin user already exists (id=%s). Skipping seed.", existing_admin.id)
            return

        email_check = await session.execute(
            select(UserModel).where(UserModel.email == settings.admin_email)
        )
        email_taken = email_check.scalar_one_or_none()

        if email_taken is not None:
            _log.warning(
                "Email %s is already taken by user id=%s (role=%s). Cannot seed admin.",
                settings.admin_email,
                email_taken.id,
                email_taken.role,
            )
            return

        hashed = hasher.hash_password(settings.admin_password)
        now = datetime.now(timezone.utc)

        admin = UserModel(
            id=uuid.uuid4(),
            email=settings.admin_email,
            hashed_password=hashed,
            display_name="Administrador",
            role=UserRole.U3.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        _log.info("Admin user seeded (id=%s, email=%s)", admin.id, settings.admin_email)
