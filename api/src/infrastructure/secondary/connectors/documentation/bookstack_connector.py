from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class BookStackConnector(IConnector):
    BASE_URL = "https://example.com/api"

    @property
    def connector_type(self) -> str:
        return "SISTEMA_DOCUMENTAL"

    @property
    def connector_implementation(self) -> str:
        return "BOOKSTACK"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "BookStack",
            "version": "1.0",
            "artifact_types": ["page", "book", "chapter"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Authorization": f"Token {config.get('token')}",
            "Accept": "application/json",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/books",
                headers=self._build_auth(config),
                params={"count": 1},
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/pages/{ref}",
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
                f"{base_url}/pages",
                headers=self._build_auth(config),
                params={
                    "count": 50,
                    "filters[book_id]": filter_params.get("book_id", ""),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])