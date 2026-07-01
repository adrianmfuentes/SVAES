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

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Wiki.js has no Confluence-style numeric page version, but a page's
        # isPublished flag is an equivalent live/draft signal: reuse the same
        # "current"/"draft" vocabulary so RV-05/RV-10 work the same way across
        # every document connector, not just Confluence.
        published = bool(data.get("isPublished", False))
        data["accessible"] = published
        data["status"] = "current" if published else "draft"
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        query = f'{{ page(path: "{ref}", locale: "en") {{ id title content isPublished updatedAt }} }}'
        response = await self._post(self._get_fetch_url(ref, config), config, {"query": query})
        response.raise_for_status()
        page = response.json().get("data", {}).get("page", {}) or {}
        return self._normalize(page)

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        query = "{ pages(orderBy: [{ field: 'updatedAt', direction: DESC }], first: 50) { results { id title path updatedAt } } }"
        response = await self._post(self._get_list_url(filter_params, config), config, {"query": query})
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("pages", {}).get("results", [])
