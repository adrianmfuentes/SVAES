from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    AtlassianAuthMixin,
)


class JiraConnector(BaseHttpConnector, AtlassianAuthMixin):
    BASE_URL = "https://api.atlassian.com"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "JIRA"

    def get_artifact_types(self) -> List[str]:
        return ["issue", "project", "board"]

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        base_url = self._get_base_url(config)
        cloud_id = config.get("cloud_id")
        if cloud_id:
            return f"{base_url}/rest/api/3/myself?cloudId={cloud_id}"
        return f"{base_url}/rest/api/3/myself"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/rest/api/3/issue/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/rest/api/3/search"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {
            "jql": filter_params.get("jql", "updated >= -1d"),
            "maxResults": filter_params.get("max_results", 50),
        }

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "issues"