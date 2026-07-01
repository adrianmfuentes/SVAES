from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class BookStackConnector(BaseHttpConnector):
    BASE_URL = "https://example.com/api"
    CONNECTOR_TYPE = "SISTEMA_DOCUMENTAL"
    CONNECTOR_IMPLEMENTATION = "BOOKSTACK"

    def get_artifact_types(self) -> List[str]:
        return ["page", "book", "chapter"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Authorization": f"Token {config.get('token')}",
            "Accept": "application/json",
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if not base.endswith("/api"):
            base += "/api"
        return base

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/books"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/pages/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # BookStack pages have no Confluence-style "status"/"version" fields
        # directly, but "draft" and "revision_count" are the equivalent native
        # signals - reuse the same "current"/"draft" vocabulary as Confluence
        # and Wiki.js so RV-05/RV-06/RV-10 work the same way across every
        # document connector.
        data["accessible"] = True
        data["status"] = "draft" if data.get("draft") else "current"
        if "revision_count" in data:
            data["version"] = str(data.get("revision_count", ""))
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return self._normalize(response.json())

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/pages"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {
            "count": 50,
            "filters[book_id]": filter_params.get("book_id", ""),
        }

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "data"