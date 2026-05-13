from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class ZammadConnector(IConnector):
    BASE_URL = "https://example.com/api/v1"

    @property
    def connector_type(self) -> str:
        return "GESTION_CAMBIOS"

    @property
    def connector_implementation(self) -> str:
        return "ZAMMAD"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Zammad",
            "version": "1.0",
            "artifact_types": ["ticket", "user", "organization"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, str]:
        token = config.get("token")
        return {
            "Accept": "application/json",
            "Authorization": f"Token {token}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/users/me",
                headers=self._build_auth(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/tickets/{ref}",
                headers=self._build_auth(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/tickets",
                headers=self._build_auth(config),
                params={
                    "state": filter_params.get("state", "open"),
                    "limit": filter_params.get("limit", 50),
                },
            )
            response.raise_for_status()
            return response.json()