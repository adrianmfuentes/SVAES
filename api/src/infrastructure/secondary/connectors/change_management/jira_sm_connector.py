from typing import Any, Dict, List
from urllib.parse import urlparse
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    AtlassianAuthMixin,
)


class JiraServiceManagementConnector(BaseHttpConnector, AtlassianAuthMixin):
    BASE_URL = "https://api.atlassian.com"
    CONNECTOR_TYPE = "GESTION_CAMBIOS"
    CONNECTOR_IMPLEMENTATION = "JIRA_SM"

    def get_artifact_types(self) -> List[str]:
        return ["request", "request_type", "approval"]

    def _get_api_base(self, config: Dict[str, Any]) -> str:
        base_url = self._get_base_url(config).rstrip("/")
        for suffix in ("/rest/servicedeskapi", "/rest/api/3", "/rest/api/2"):
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)]
                break
        site_id = config.get("site_id")
        if site_id and urlparse(base_url).netloc == "api.atlassian.com":
            return f"{base_url}/ex/jira/{site_id}"
        return base_url

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_api_base(config)}/rest/servicedeskapi/servicedesk"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_api_base(config)}/rest/servicedeskapi/request/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        service_desk_id = config.get("service_desk_id")
        base = self._get_api_base(config)
        if service_desk_id:
            return f"{base}/rest/servicedeskapi/servicedesk/{service_desk_id}/queue"
        return f"{base}/rest/servicedeskapi/request"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        service_desk_id = config.get("service_desk_id")
        if service_desk_id:
            return {"requestType": filter_params.get("request_type"), "limit": 50}
        return {"limit": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "values"