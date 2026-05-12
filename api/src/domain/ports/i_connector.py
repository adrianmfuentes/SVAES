from abc import ABC, abstractmethod
from typing import Any, Dict, List

class IConnector(ABC):
    """Outbound port for interacting with external systems through connectors. This interface abstracts 
    the operations that can be performed on a connector, allowing the application layer to interact 
    with various external systems without being coupled to specific implementations.

    Methods:
            test_connection(config: Dict[str, Any]) -> bool: Checks if the provided configuration allows successful communication with the external system.
            fetch_artifact(ref: str, config: Dict[str, Any]) -> Dict[str, Any]: Retrieves and normalizes the data of a specific artifact from the external system.
            list_artifacts(filter_params: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]: Retrieves a list of artifacts from the external system that match the given filter parameters.
            get_metadata() -> Dict[str, Any]: Returns metadata about the connector type, version, and expected JSON configuration schema.
    """
    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_artifacts(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        pass