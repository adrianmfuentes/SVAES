from features.connectors.infrastructure.gateways.connector_registry import ConnectorRegistry
from features.connectors.infrastructure.gateways.task_management import JiraConnector, LinearConnector, TrelloConnector, AsanaConnector
from features.connectors.infrastructure.gateways.source_control import GitLabConnector, GitHubConnector, BitbucketConnector, GiteaConnector
from features.connectors.infrastructure.gateways.documentation import ConfluenceConnector, NotionConnector, WikiJsConnector, BookStackConnector
from features.connectors.infrastructure.gateways.planning import ClickUpConnector, TaigaConnector, PlaneConnector, MiroConnector
from features.connectors.infrastructure.gateways.change_management import JiraServiceManagementConnector, GLPiConnector, ZammadConnector, RedmineConnector
from features.connectors.infrastructure.gateways.generic import GenericHttpConnector


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