import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
from infrastructure.secondary.database.models.user_model import UserModel
from infrastructure.secondary.database.models.profile_model import VerificationProfileModel
from infrastructure.secondary.database.models.rule_model import VerificationRuleModel
from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
from domain.enums import UserRole, SeverityType
from core.config import Settings
from core.rule_names import RULE_NAMES

_log = logging.getLogger(__name__)

_SYSTEM_RULES = [
    ("RV-01", SeverityType.HIGH,   RULE_NAMES["RV-01"]),
    ("RV-02", SeverityType.HIGH,   RULE_NAMES["RV-02"]),
    ("RV-03", SeverityType.MEDIUM, RULE_NAMES["RV-03"]),
    ("RV-04", SeverityType.MEDIUM, RULE_NAMES["RV-04"]),
    ("RV-05", SeverityType.HIGH,   RULE_NAMES["RV-05"]),
    ("RV-06", SeverityType.MEDIUM, RULE_NAMES["RV-06"]),
    ("RV-07", SeverityType.HIGH,   RULE_NAMES["RV-07"]),
    ("RV-08", SeverityType.HIGH,   RULE_NAMES["RV-08"]),
    ("RV-09", SeverityType.MEDIUM, RULE_NAMES["RV-09"]),
    ("RV-10", SeverityType.HIGH,   RULE_NAMES["RV-10"]),
]


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
            if hasher.needs_rehash(existing_admin.hashed_password):
                password_matches = await asyncio.to_thread(
                    hasher.verify_password, settings.admin_password, existing_admin.hashed_password
                )
                if password_matches:
                    existing_admin.hashed_password = await asyncio.to_thread(
                        hasher.hash_password, settings.admin_password
                    )
                    await session.commit()
                    _log.info(
                        "Admin password rehashed to rounds=%d (id=%s)",
                        hasher.ROUNDS,
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

        hashed = await asyncio.to_thread(hasher.hash_password, settings.admin_password)
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


async def seed_system_profile() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(VerificationProfileModel)
            .where(VerificationProfileModel.is_system == True)
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            _log.info("System verification profile already exists. Skipping seed.")
            return

        now = datetime.now(timezone.utc)
        profile_id = uuid.uuid4()

        profile = VerificationProfileModel(
            id=profile_id,
            organization_id=None,
            name="Perfil por defecto",
            description="Perfil del sistema con las 10 reglas de verificación estándar. No puede ser eliminado.",
            is_default=False,
            is_system=True,
            rules=[],
            created_at=now,
            updated_at=now,
        )
        session.add(profile)
        await session.flush()

        for order, (template, severity, _label) in enumerate(_SYSTEM_RULES):
            rule = VerificationRuleModel(
                id=uuid.uuid4(),
                profile_id=profile_id,
                rule_template=template,
                severity=severity.value,
                params={},
                connector_instance_id=None,
                display_order=order,
                is_active=True,
                created_at=now,
            )
            session.add(rule)

        await session.commit()
        _log.info("System verification profile seeded (id=%s) with %d rules.", profile_id, len(_SYSTEM_RULES))
