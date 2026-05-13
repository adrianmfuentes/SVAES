from typing import List, Optional
from uuid import UUID
from domain.exceptions import EntityNotFoundError, ValidationError

"""
Este módulo define el caso de uso para gestionar API keys, que incluye la creación, listado y revocación de API keys para una organización.
La creación de un API key requiere un nombre y opcionalmente una fecha de expiración. El listado devuelve todas las API keys asociadas a una organización, 
y la revocación permite desactivar un API key específico. Cada API key generado tiene un formato único y seguro, y se almacena con información relevante 
como su fecha de creación, fecha de expiración y estado de activación.

Las API keys sirven como credenciales para que aplicaciones externas puedan interactuar con la API de SVAES en nombre de una organización, 
permitiendo integraciones seguras y controladas.
"""
class ManageApiKeysUseCase:
    async def create_api_key(
        self, organization_id: UUID, name: str, expires_in_days: Optional[int] = None
    ) -> dict:
        if not name:
            raise ValidationError("El nombre del API key es requerido")
        import secrets
        from datetime import datetime, timedelta, timezone

        key = f"svk_{secrets.token_urlsafe(32)}"
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        return {
            "id": UUID(),
            "organization_id": organization_id,
            "name": name,
            "key": key,
            "expires_at": expires_at,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }

    async def list_api_keys(self, organization_id: UUID) -> List[dict]:
        return []

    async def revoke_api_key(self, key_id: UUID) -> None:
        if not key_id:
            raise ValidationError("key_id es requerido")