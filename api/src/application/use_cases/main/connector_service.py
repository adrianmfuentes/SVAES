from typing import List, Optional
from uuid import UUID
from application.ports.input.i_connector_service import IConnectorService
from application.ports.output.i_connector_repository import IConnectorRepository
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError, ValidationError

from infrastructure.secondary.connectors.jira_connector import JiraConnector
from infrastructure.secondary.connectors.gitlab_connector import GitLabConnector
from infrastructure.secondary.connectors.confluence_connector import ConfluenceConnector

"""
Este módulo define el servicio de conector, que es responsable de gestionar los conectores dentro del sistema. Incluye la lógica de negocio para 
registrar nuevos conectores, actualizar su configuración, probar la conexión, listar conectores de una organización, obtener detalles de un conector 
específico, eliminar conectores y activar/desactivar conectores.
"""
class ConnectorService(IConnectorService):
    def __init__(self, connector_repository: IConnectorRepository) -> None:
        self._connector_repo = connector_repository


    async def register_connector(
        self,
        organization_id: UUID,
        connector_type: str,
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

        connector_impl = self._get_connector_impl(connector.connector_type)
        if not connector_impl:
            raise ValidationError(f"Tipo de conector no soportado: {connector.connector_type}")

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


    def _get_connector_impl(self, connector_type: str):
        connectors = {
            "JIRA": JiraConnector,
            "GITLAB": GitLabConnector,
            "CONFLUENCE": ConfluenceConnector,
        }
        connector_class = connectors.get(connector_type.upper())
        if connector_class:
            return connector_class()
        return None


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