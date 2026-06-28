from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class GLPiConnector(BaseHttpConnector):
    BASE_URL = "https://example.com/apirest.php"
    CONNECTOR_TYPE = "GESTION_CAMBIOS"
    CONNECTOR_IMPLEMENTATION = "GLPI"

    def get_artifact_types(self) -> List[str]:
        return ["ticket", "change", "problem"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "App-Token": config.get("app_token", ""),
            "Authorization": f"user_token {config.get('user_token')}",
            "Content-Type": "application/json",
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if "apirest.php" not in base:
            base += "/apirest.php"
        return base

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/initSession"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/Ticket/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return {"show": "1"}

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        item_type = filter_params.get("item_type", "Ticket")
        return f"{self._get_base_url(config)}/{item_type}"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {"range": f"0-{filter_params.get('limit', 50)}"}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""