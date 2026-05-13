from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class NotionConnector(IConnector):
    BASE_URL = "https://api.notion.com/v1"

    @property
    def connector_type(self) -> str:
        return "SISTEMA_DOCUMENTAL"

    @property
    def connector_implementation(self) -> str:
        return "NOTION"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Notion",
            "version": "1.0",
            "artifact_types": ["page", "database"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Notion-Version": "2022-06-28",
            "Authorization": f"Bearer {config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/users/me",
                headers=self._build_headers(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/pages/{ref}",
                headers=self._build_headers(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            database_id = config.get("database_id")
            if database_id:
                response = await client.post(
                    f"{self.BASE_URL}/databases/{database_id}/query",
                    headers=self._build_headers(config),
                    json={"page_size": 50},
                )
            else:
                response = await client.post(
                    f"{self.BASE_URL}/search",
                    headers=self._build_headers(config),
                    json={"filter": {"value": "page", "property": "object"}, "page_size": 50},
                )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])