from typing import Any

class ConnectorRegistry:
    """Registry for managing connector implementations. This class allows for the registration and retrieval of connectors based on their type, 
    enabling the application to interact with various external systems through a unified interface.

    Methods:
        register(connector_type: str, connector: Any) -> None: Registers a connector implementation
        get_connector(connector_type: str) -> Any: Retrieves the connector implementation for the given type, raising a KeyError if the type is not registered.
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
