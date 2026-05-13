from typing import Any, Dict, List, Optional
import httpx
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    BASE_URL: str = ""
    TIMEOUT: float = 30.0

    @property
    @abstractmethod
    def connector_type(self) -> str:
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        pass

    def _get_config_value(self, config: Dict[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
        return config.get(key, default)

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {"Accept": "application/json"}

    def _build_auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {}

    async def _get(self, path: str, config: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        base_url = self._get_config_value(config, "base_url", self.BASE_URL)
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            headers = {**self._build_headers(config), **self._build_auth_headers(config)}
            url = f"{base_url}{path}"
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response

    async def _post(self, path: str, config: Dict[str, Any], json: Optional[Dict[str, Any]] = None) -> httpx.Response:
        base_url = self._get_config_value(config, "base_url", self.BASE_URL)
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            headers = {**self._build_headers(config), **self._build_auth_headers(config)}
            url = f"{base_url}{path}"
            response = await client.post(url, headers=headers, json=json)
            response.raise_for_status()
            return response

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        raise NotImplementedError

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def list_artifacts(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError