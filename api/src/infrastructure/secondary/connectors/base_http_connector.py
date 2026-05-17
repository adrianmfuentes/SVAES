from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar
import httpx

T = TypeVar("T")


class BaseHttpConnector(ABC):
    BASE_URL: str = ""
    CONNECTOR_TYPE: str = ""
    CONNECTOR_IMPLEMENTATION: str = ""
    TIMEOUT: float = 30.0
    CONTENT_TYPE: str = "application/json"

    @property
    def connector_type(self) -> str:
        return self.CONNECTOR_TYPE

    @property
    def connector_implementation(self) -> str:
        return self.CONNECTOR_IMPLEMENTATION

    def get_connector_type(self) -> str:
        return self.CONNECTOR_TYPE

    def get_connector_implementation(self) -> str:
        return self.CONNECTOR_IMPLEMENTATION

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.__class__.__name__.replace("Connector", ""),
            "version": "1.0",
            "artifact_types": self.get_artifact_types(),
        }

    @abstractmethod
    def get_artifact_types(self) -> List[str]:
        pass

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        raise NotImplementedError("Subclasses must implement _build_headers")

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        return config.get("base_url", self.BASE_URL)

    async def _get(
        self, url: str, config: Dict[str, Any], params: Dict[str, Any] | None = None
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(url, headers=self._build_headers(config), params=params)
            return response

    async def _post(
        self, url: str, config: Dict[str, Any], json: Dict[str, Any] | None = None
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.post(url, headers=self._build_headers(config), json=json)
            return response

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        url = self._get_health_url(config)
        response = await self._get(url, config)
        return response.status_code == 200

    @abstractmethod
    def _get_health_url(self, config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        pass

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return response.json()

    @abstractmethod
    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def _get_results_key(self) -> str:
        pass

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        url = self._get_list_url(filter_params, config)
        json_body = self._get_list_json(filter_params, config)
        if json_body is not None:
            response = await self._post(url, config, json_body)
        else:
            response = await self._get(url, config, self._get_list_params(filter_params, config))
        response.raise_for_status()
        data = response.json()
        return data.get(self._get_results_key(), [])


class BearerAuthMixin:
    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": BaseHttpConnector.CONTENT_TYPE,
            "Authorization": f"Bearer {config.get('token')}",
        }


class AtlassianAuthMixin:
    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": BaseHttpConnector.CONTENT_TYPE,
            "email": config.get("email", "") or "",
            "api_token": config.get("api_token", "") or "",
        }


class ApiKeyAuthMixin:
    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": BaseHttpConnector.CONTENT_TYPE,
            "Authorization": f"Bearer {config.get('token')}",
        }