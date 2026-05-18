from typing import Any, Optional
from application.ports.output.i_connector_registry import IConnectorRegistry


class ConnectorRegistry(IConnectorRegistry):
    def __init__(self) -> None:
        self._by_type: dict[str, Any] = {}
        self._by_implementation: dict[str, Any] = {}

    def register(self, connector_type: str, connector: Any) -> None:
        ct = connector_type.upper()
        impl = connector.get_connector_implementation().upper()
        self._by_type[ct] = connector
        self._by_implementation[impl] = connector

    def get_by_implementation(self, impl_name: str) -> Any:
        connector = self._by_implementation.get(impl_name.upper())
        if connector is None:
            raise KeyError(f"Implementation '{impl_name}' no registrada")
        return connector

    def get_by_type(self, connector_type: str) -> Optional[Any]:
        return self._by_type.get(connector_type.upper())

    def get_by_type_safe(self, connector_type: str) -> Optional[Any]:
        return self._by_type.get(connector_type.upper())

    def list_by_type(self, connector_type: str) -> list[Any]:
        connector = self._by_type.get(connector_type.upper())
        return [connector] if connector else []

    def list_all_implementations(self) -> list[str]:
        return list(self._by_implementation.keys())