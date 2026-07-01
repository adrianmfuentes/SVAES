from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_graphql_connector import BaseGraphQLConnector


class LinearConnector(BaseGraphQLConnector):
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

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        query = {"query": "{ viewer { id } }"}
        response = await self._post(self._get_base_url(config), config, query)
        return response.status_code == 200

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        state = data.get("state") or {}
        if isinstance(state, dict) and "name" in state:
            data["status"] = state["name"]
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        query = {
            "query": f"{{ issue(id: \"{ref}\") {{ id identifier title state {{ name }} assignee {{ name }} createdAt updatedAt }} }}"
        }
        response = await self._post(self._get_base_url(config), config, query)
        response.raise_for_status()
        issue = response.json().get("data", {}).get("issue", {})
        return self._normalize(issue)

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        query = {
            "query": f"{{ issues(first: {filter_params.get('first', 50)}) {{ nodes {{ id identifier title state {{ name }} createdAt updatedAt }} }} }}"
        }
        response = await self._post(self._get_base_url(config), config, query)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("issues", {}).get("nodes", [])
