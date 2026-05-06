from typing import Any

class ConnectorRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, Any] = {}

    def register(self, connector_type: str, connector: Any) -> None:
        self._registry[connector_type] = connector

    def get_connector(self, connector_type: str) -> Any:
        connector = self._registry.get(connector_type)
        if connector is None:
            raise KeyError(f"Connector type '{connector_type}' not registered")
        return connector
