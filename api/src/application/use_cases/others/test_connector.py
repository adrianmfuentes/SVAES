from uuid import UUID
from application.ports.output.i_connector_repository import IConnectorRepository
from domain.exceptions import EntityNotFoundError, ValidationError
from infrastructure.secondary.connectors.jira_connector import JiraConnector
from infrastructure.secondary.connectors.gitlab_connector import GitLabConnector
from infrastructure.secondary.connectors.confluence_connector import ConfluenceConnector


class TestConnectorUseCase:
    def __init__(self, connector_repository: IConnectorRepository) -> None:
        self._connector_repo = connector_repository

    async def execute(self, connector_id: UUID) -> dict:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        connector_impl = self._get_connector_impl(connector.connector_type)
        if not connector_impl:
            raise ValidationError(f"Tipo de conector no soportado: {connector.connector_type}")

        try:
            result = connector_impl.test_connection(connector)
            return {"success": result, "connector_id": str(connector_id)}
        except Exception as e:
            return {"success": False, "connector_id": str(connector_id), "error": str(e)}

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