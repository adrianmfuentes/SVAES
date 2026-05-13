from abc import ABC, abstractmethod
from typing import Any, Dict, List

class IConnector(ABC):
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