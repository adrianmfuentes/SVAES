from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    BearerAuthMixin,
)


class NotionConnector(BaseHttpConnector, BearerAuthMixin):
    BASE_URL = "https://api.notion.com/v1"
    CONNECTOR_TYPE = "SISTEMA_DOCUMENTAL"
    CONNECTOR_IMPLEMENTATION = "NOTION"

    def get_artifact_types(self) -> List[str]:
        return ["page", "database"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Notion-Version": "2022-06-28",
            "Authorization": f"Bearer {config.get('token')}",
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/users/me"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/pages/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        database_id = config.get("database_id")
        if database_id:
            return f"{self.BASE_URL}/databases/{database_id}/query"
        return f"{self.BASE_URL}/search"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        database_id = config.get("database_id")
        if database_id:
            return {"page_size": 50}
        return {"filter": {"value": "page", "property": "object"}, "page_size": 50}

    def _get_results_key(self) -> str:
        return "results"