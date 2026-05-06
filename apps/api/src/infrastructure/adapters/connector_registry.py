from typing import Any

class ConnectorRegistry:
    """In-memory registry mapping connector type identifiers to IConnector implementations.

    Populated at application startup. Acts as a Service Locator for the infrastructure
    adapter layer, allowing ConfigureConnectorUseCase to remain decoupled from concrete
    connector classes.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Any] = {}

    def register(self, connector_type: str, connector: Any) -> None:
        self._registry[connector_type] = connector

    def get_connector(self, connector_type: str) -> Any:
        """Returns the IConnector implementation for the given type.

        Raises:
            KeyError: If the connector type has not been registered.
        """
        connector = self._registry.get(connector_type)
        if connector is None:
            raise KeyError(f"Connector type '{connector_type}' not registered")
        return connector
