from typing import List, Optional
from uuid import UUID
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from domain.entities.api_key import APIKey
from domain.exceptions import EntityNotFoundError, ValidationError
from application.ports.output.i_api_key_repository import IAPIKeyRepository
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)


class ManageApiKeysUseCase:
    def __init__(self, api_key_repository: IAPIKeyRepository) -> None:
        self._repo = api_key_repository

    async def create_api_key(
        self, organization_id: UUID, name: str, expires_in_days: Optional[int] = None
    ) -> dict:
        if not name:
            raise ValidationError("El nombre del API key es requerido")

        raw_key = f"svk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:12]
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = APIKey(
            id=UUID(),
            organization_id=organization_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        saved = await self._repo.save(api_key)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.API_KEY_CREATED,
            user_id=UUID(),
            organization_id=organization_id,
            resource_type="api_key",
            resource_id=saved.id,
            details={"name": name, "expires_in_days": expires_in_days},
        ))
        _log.info("API key created: org=%s name=%s id=%s", organization_id, name, saved.id)

        return {
            "id": str(saved.id),
            "organization_id": str(saved.organization_id),
            "name": saved.name,
            "key": raw_key,
            "prefix": saved.prefix,
            "expires_at": saved.expires_at.isoformat() if saved.expires_at else None,
            "is_active": saved.is_active,
            "created_at": saved.created_at.isoformat(),
        }

    async def list_api_keys(self, organization_id: UUID) -> List[dict]:
        keys = await self._repo.list_by_organization(organization_id)
        return [
            {
                "id": str(k.id),
                "name": k.name,
                "prefix": k.prefix,
                "is_active": k.is_active,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]

    async def revoke_api_key(self, key_id: UUID) -> dict:
        if not key_id:
            raise ValidationError("key_id es requerido")

        api_key = await self._repo.get_by_id(key_id)
        if not api_key:
            raise EntityNotFoundError(f"API key no encontrado: {key_id}")

        api_key.is_active = False
        updated = await self._repo.update(api_key)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.API_KEY_REVOKED,
            user_id=UUID(),
            organization_id=api_key.organization_id,
            resource_type="api_key",
            resource_id=key_id,
            details={"name": api_key.name},
        ))
        _log.info("API key revoked: id=%s org=%s", key_id, api_key.organization_id)

        return {"id": str(updated.id), "is_active": updated.is_active}

    async def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = await self._repo.get_by_hash(key_hash)
        if not api_key:
            return None
        if not api_key.is_active:
            return None
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None
        api_key.last_used_at = datetime.now(timezone.utc)
        await self._repo.update(api_key)
        return api_key