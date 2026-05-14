from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class PlaneConnector(BaseHttpConnector):
    BASE_URL = "https://api.plane.io/api/v1"
    CONNECTOR_TYPE = "HERRAMIENTA_PLANIFICACION"
    CONNECTOR_IMPLEMENTATION = "PLANE"

    def get_artifact_types(self) -> List[str]:
        return ["issue", "cycle", "module", "project"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "x-api-key": config.get("api_key", ""),
            "x-api-host": config.get("instance_url", ""),
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        workspace = config.get("workspace")
        return f"{self.BASE_URL}/workspaces/{workspace}/projects"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        workspace = config.get("workspace")
        return f"{self.BASE_URL}/workspaces/{workspace}/issues/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        workspace = config.get("workspace")
        project = config.get("project")
        if project:
            return f"{self.BASE_URL}/workspaces/{workspace}/projects/{project}/issues"
        return f"{self.BASE_URL}/workspaces/{workspace}/issues"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        project = config.get("project")
        if project:
            return {"cycle": filter_params.get("cycle")}
        return None

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "results"