from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class LinearConnector(IConnector):
    BASE_URL = "https://api.linear.app/graphql"

    @property
    def connector_type(self) -> str:
        return "GESTOR_TAREAS"

    @property
    def connector_implementation(self) -> str:
        return "LINEAR"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Linear",
            "version": "1.0",
            "artifact_types": ["issue", "cycle", "project"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.get('api_key')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        query = {"query": "{ viewer { id } }"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.BASE_URL,
                headers=self._build_headers(config),
                json=query,
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        query = {
            "query": f"{{ issue(id: \"{ref}\") {{ id identifier title state {{ name }} assignee {{ name }} createdAt updatedAt }} }}"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.BASE_URL,
                headers=self._build_headers(config),
                json=query,
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        query = {
            "query": f"{{ issues(first: {filter_params.get('first', 50)}) {{ nodes {{ id identifier title state {{ name }} createdAt updatedAt }} }} }}"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.BASE_URL,
                headers=self._build_headers(config),
                json=query,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("issues", {}).get("nodes", [])