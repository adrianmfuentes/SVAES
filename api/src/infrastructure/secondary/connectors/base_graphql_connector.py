from typing import Any, Dict
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class BaseGraphQLConnector(BaseHttpConnector):
    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return self.BASE_URL

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return self.BASE_URL

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return self.BASE_URL

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

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
