from typing import Any

"""
Este módulo define la clase `ConnectorRegistry`, que es un registro para almacenar y recuperar conectores de diferentes tipos.
La clase proporciona métodos para registrar un conector bajo un tipo específico y para obtener un conector registrado por su tipo.
"""
class ConnectorRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, Any] = {}

    def register(self, connector_type: str, connector: Any) -> None:
        self._registry[connector_type] = connector

    def get_connector(self, connector_type: str) -> Any:
        connector = self._registry.get(connector_type)
        if connector is None:
            raise KeyError(f"Connector de tipo '{connector_type}' no registrado")
        return connector
