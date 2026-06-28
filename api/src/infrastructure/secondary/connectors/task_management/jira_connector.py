from typing import Any, Dict, List
from urllib.parse import urlparse
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    AtlassianAuthMixin,
)


class JiraConnector(AtlassianAuthMixin, BaseHttpConnector):
    BASE_URL = "https://api.atlassian.com"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "JIRA"

    def get_artifact_types(self) -> List[str]:
        return ["issue", "project", "board"]

    def _get_api_base(self, config: Dict[str, Any]) -> str:
        base_url = self._get_base_url(config).rstrip("/")
        cloud_id = config.get("cloud_id")
        if cloud_id and urlparse(base_url).netloc == "api.atlassian.com":
            return f"{base_url}/ex/jira/{cloud_id}"
        return base_url

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_api_base(config)}/rest/api/3/myself"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_api_base(config)}/rest/api/3/issue/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_api_base(config)}/rest/api/3/search/jql"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {
            "jql": filter_params.get("jql", "order by updated desc"),
            "maxResults": filter_params.get("max_results", 50),
        }

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "issues"