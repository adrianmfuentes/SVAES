from typing import List, Optional
from uuid import UUID, uuid4
from application.ports.input.i_connector_service import IConnectorService
from application.ports.output.i_connector_repository import IConnectorRepository
from application.ports.output.i_connector_registry import IConnectorRegistry
from core.config import settings
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError

_log = get_logger(__name__)


class ConnectorService(IConnectorService):
    def __init__(
        self,
        connector_repository: IConnectorRepository,
        connector_registry: IConnectorRegistry,
    ) -> None:
        self._connector_repo = connector_repository
        self._connector_registry = connector_registry


    async def register_connector(
        self,
        organization_id: UUID,
        connector_type: str,
        connector_implementation: str,
        name: str,
        config: dict,
        requested_by: UUID,
    ) -> ConnectorInstance:
        existing = await self._connector_repo.list_by_organization(organization_id, active_only=False, skip=0, limit=1000)
        for c in existing:
            if c.connector_implementation == connector_implementation:
                raise DuplicateEntityError(f"Ya existe un conector {connector_implementation} en esta organización")

        from cryptography.fernet import Fernet

        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
        encrypted_credentials = fernet.encrypt(str(config).encode())

        connector = ConnectorInstance(
            id=uuid4(),
            organization_id=organization_id,
            connector_type=connector_type,
            connector_implementation=connector_implementation,
            name=name,
            encrypted_credentials=encrypted_credentials,
            status=ConnectorStatus.ACTIVO,
        )
        saved = await self._connector_repo.save(connector)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_CREATED,
            user_id=requested_by,
            organization_id=organization_id,
            resource_type="connector",
            resource_id=saved.id,
            details={"name": name, "type": connector_type},
        ))
        _log.info("Connector registered: org=%s type_len=%d", organization_id, len(connector_type))

        return saved


    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        requested_by: Optional[UUID] = None,
    ) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        if name:
            connector.name = name
        if config:
            from cryptography.fernet import Fernet
            fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
            connector.encrypted_credentials = fernet.encrypt(str(config).encode())

        updated = await self._connector_repo.update(connector)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_UPDATED,
            user_id=requested_by or uuid4(),
            organization_id=connector.organization_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"name": connector.name} if name else {},
        ))
        _log.info("Connector updated: id=%s org=%s", connector_id, connector.organization_id)

        return updated


    async def test_connector_connection(self, connector_id: UUID, requested_by: UUID) -> bool:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        from domain.exceptions import ConnectorConnectionFailedError
        from application.ports.output.i_connector import IConnector

        connector_impl = self._get_connector_impl(connector.connector_implementation)
        if not connector_impl:
            raise ValidationError(f"Implementación '{connector.connector_implementation}' no soportada")

        from cryptography.fernet import Fernet
        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
        decrypted_config = eval(fernet.decrypt(connector.encrypted_credentials).decode())

        try:
            result = connector_impl.test_connection(decrypted_config)
            if result:
                connector.status = ConnectorStatus.ACTIVO
                await self._connector_repo.update(connector)

            audit = get_audit_logger()
            audit.log(AuditEntry(
                event=AuditEvent.CONNECTOR_TESTED,
                user_id=requested_by,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector_id,
                details={"success": result, "implementation": connector.connector_implementation},
            ))
            _log.info("Connector tested: id=%s org=%s result=%s", connector_id, connector.organization_id, result)

            return result
        except Exception:
            connector.status = ConnectorStatus.ERROR
            await self._connector_repo.update(connector)
            raise ConnectorConnectionFailedError(f"Error al probar conexión del conector: {connector_id}")


    def _get_connector_impl(self, connector_implementation: str):
        connector_impl = self._connector_registry.get_by_implementation(connector_implementation)
        return connector_impl


    async def list_connectors(
        self,
        organization_id: UUID,
        active_only: bool = True,
    ) -> List[ConnectorInstance]:
        return await self._connector_repo.list_by_organization(
            organization_id, active_only=active_only, skip=0, limit=50
        )


    async def get_connector(self, connector_id: UUID) -> Optional[ConnectorInstance]:
        return await self._connector_repo.get_by_id(connector_id)


    async def delete_connector(self, connector_id: UUID, requested_by: UUID) -> None:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        org_id = connector.organization_id
        await self._connector_repo.delete(connector_id)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_DELETED,
            user_id=requested_by,
            organization_id=org_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"name": connector.name},
        ))
        _log.info("Connector deleted: id=%s org=%s", connector_id, org_id)


    async def toggle_connector_status(
        self, connector_id: UUID, status: ConnectorStatus, requested_by: UUID
    ) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        connector.status = status
        return await self._connector_repo.update(connector)