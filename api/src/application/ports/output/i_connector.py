from abc import ABC, abstractmethod
from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class IConnector(Protocol):
    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        pass


class YouTubeConnector(IConnector):
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        raise NotImplementedError

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_metadata(self) -> Dict[str, Any]:
        return {"name": "YouTube", "version": "1.0", "artifact_types": ["video", "playlist"]}


class YouTube:
    def __call__(self) -> YouTubeConnector:
        return YouTubeConnector()