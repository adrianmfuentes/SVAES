from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class LinearConnector(BaseHttpConnector):
    BASE_URL = "https://api.linear.app/graphql"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "LINEAR"

    def get_artifact_types(self) -> List[str]:
        return ["issue", "cycle", "project"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.get('api_key')}",
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return self.BASE_URL

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return self.BASE_URL

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return self.BASE_URL

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        query = {"query": "{ viewer { id } }"}
        response = await self._post(self.BASE_URL, config, query)
        return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        query = {
            "query": f"{{ issue(id: \"{ref}\") {{ id identifier title state {{ name }} assignee {{ name }} createdAt updatedAt }} }}"
        }
        response = await self._post(self.BASE_URL, config, query)
        response.raise_for_status()
        return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        query = {
            "query": f"{{ issues(first: {filter_params.get('first', 50)}) {{ nodes {{ id identifier title state {{ name }} createdAt updatedAt }} }} }}"
        }
        response = await self._post(self.BASE_URL, config, query)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("issues", {}).get("nodes", [])