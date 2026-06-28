from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_graphql_connector import BaseGraphQLConnector


class WikiJsConnector(BaseGraphQLConnector):
    BASE_URL = "http://localhost:3000"
    CONNECTOR_TYPE = "SISTEMA_DOCUMENTAL"
    CONNECTOR_IMPLEMENTATION = "WIKIJS"

    def get_artifact_types(self) -> List[str]:
        return ["page", "asset"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {config.get('token')}",
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if base.endswith("/graphql"):
            base = base[:-8]
        return base

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/graphql"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/graphql"

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/graphql"

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        query = {"query": "{ users { total } }"}
        response = await self._post(self._get_health_url(config), config, query)
        return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        query = f'{{ page(location: "{{{{ path: "{ref}" }}}}") {{ id title content updatedAt }} }}'
        response = await self._post(self._get_fetch_url(ref, config), config, {"query": query})
        response.raise_for_status()
        return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        query = "{ pages(orderBy: [{ field: 'updatedAt', direction: DESC }], first: 50) { results { id title path updatedAt } } }"
        response = await self._post(self._get_list_url(filter_params, config), config, {"query": query})
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("pages", {}).get("results", [])
