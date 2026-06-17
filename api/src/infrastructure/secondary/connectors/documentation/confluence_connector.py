from typing import Any, Dict, List
import base64
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
)


class ConfluenceConnector(BaseHttpConnector):
    BASE_URL = "https://your-site.atlassian.net"
    CONNECTOR_TYPE = "SISTEMA_DOCUMENTAL"
    CONNECTOR_IMPLEMENTATION = "CONFLUENCE"

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        email = config.get("email", "") or ""
        api_token = config.get("api_token", "") or ""
        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        return {
            "Accept": self.CONTENT_TYPE,
            "Authorization": f"Basic {credentials}",
        }

    def get_artifact_types(self) -> List[str]:
        return ["page", "space", "blogpost"]

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        base_url = self._get_base_url(config)
        cloud_id = config.get("cloud_id")
        if cloud_id:
            return f"{base_url}/wiki/rest/api/user/current?cloudId={cloud_id}"
        return f"{base_url}/wiki/rest/api/user/current"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/wiki/rest/api/content/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return {"expand": "version"}

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/wiki/rest/api/content/search"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        space_key = filter_params.get("space_key") or config.get("space_key")
        cql = filter_params.get("cql", "type page order by lastmodified desc")
        if space_key:
            cql = f"space={space_key} AND {cql}"
        return {"cql": cql, "limit": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "results"