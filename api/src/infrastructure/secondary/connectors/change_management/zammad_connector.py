from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class ZammadConnector(BaseHttpConnector):
    BASE_URL = "https://example.com/api/v1"
    CONNECTOR_TYPE = "GESTION_CAMBIOS"
    CONNECTOR_IMPLEMENTATION = "ZAMMAD"

    def get_artifact_types(self) -> List[str]:
        return ["ticket", "user", "organization"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        token = config.get("token")
        return {
            "Accept": "application/json",
            "Authorization": f"Token {token}",
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        return config.get("base_url", self.BASE_URL)

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/users/me"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/tickets/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/tickets"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {
            "state": filter_params.get("state", "open"),
            "limit": filter_params.get("limit", 50),
        }

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""