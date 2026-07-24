from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
from infrastructure.secondary.connectors.task_management import JiraConnector, LinearConnector, TrelloConnector, AsanaConnector
from infrastructure.secondary.connectors.source_control import GitLabConnector, GitHubConnector, BitbucketConnector, GiteaConnector
from infrastructure.secondary.connectors.documentation import ConfluenceConnector, NotionConnector, WikiJsConnector, BookStackConnector
from infrastructure.secondary.connectors.planning import ClickUpConnector, TaigaConnector, PlaneConnector, MiroConnector
from infrastructure.secondary.connectors.change_management import JiraServiceManagementConnector, GLPiConnector, ZammadConnector, RedmineConnector
from infrastructure.secondary.connectors.generic import GenericHttpConnector


def create_registered_connector_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    for connector_impl in [
        JiraConnector(),
        LinearConnector(),
        TrelloConnector(),
        AsanaConnector(),
        GitLabConnector(),
        GitHubConnector(),
        BitbucketConnector(),
        GiteaConnector(),
        ConfluenceConnector(),
        NotionConnector(),
        WikiJsConnector(),
        BookStackConnector(),
        ClickUpConnector(),
        TaigaConnector(),
        PlaneConnector(),
        MiroConnector(),
        JiraServiceManagementConnector(),
        GLPiConnector(),
        ZammadConnector(),
        RedmineConnector(),
        GenericHttpConnector(),
    ]:
        registry.register(connector_impl.get_connector_implementation(), connector_impl)
    return registry