from typing import List, Optional
from uuid import UUID
from application.ports.input.i_connector_service import IConnectorService
from application.ports.output.i_connector_repository import IConnectorRepository
from application.ports.output.i_connector_registry import IConnectorRegistry
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError, ValidationError


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
    ) -> ConnectorInstance:
        from cryptography.fernet import Fernet
        import base64

        key = base64.urlsafe_b64encode(b"SVAES_ENCRYPTION_KEY_32_BYTES!!")
        fernet = Fernet(key)
        encrypted_credentials = fernet.encrypt(str(config).encode())

        connector = ConnectorInstance(
            id=UUID(),
            organization_id=organization_id,
            connector_type=connector_type,
            connector_implementation=connector_implementation,
            name=name,
            encrypted_credentials=encrypted_credentials,
            status=ConnectorStatus.INACTIVO,
        )
        return await self._connector_repo.save(connector)


    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        if name:
            connector.name = name
        if config:
            from cryptography.fernet import Fernet
            import base64
            key = base64.urlsafe_b64encode(b"SVAES_ENCRYPTION_KEY_32_BYTES!!")
            fernet = Fernet(key)
            connector.encrypted_credentials = fernet.encrypt(str(config).encode())

        return await self._connector_repo.update(connector)


    async def test_connector_connection(self, connector_id: UUID) -> bool:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        from domain.exceptions import ConnectorConnectionFailedError
        from application.ports.output.i_connector import IConnector

        connector_impl = self._get_connector_impl(connector.connector_implementation)
        if not connector_impl:
            raise ValidationError(f"Implementación '{connector.connector_implementation}' no soportada")

        try:
            result = connector_impl.test_connection(connector)
            if result:
                connector.status = ConnectorStatus.ACTIVO
                await self._connector_repo.update(connector)
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


    async def delete_connector(self, connector_id: UUID) -> None:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        await self._connector_repo.delete(connector_id)


    async def toggle_connector_status(
        self, connector_id: UUID, status: ConnectorStatus
    ) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        connector.status = status
        return await self._connector_repo.update(connector)