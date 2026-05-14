from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class TaigaConnector(BaseHttpConnector):
    BASE_URL = "https://api.taiga.io/api/v1"
    CONNECTOR_TYPE = "HERRAMIENTA_PLANIFICACION"
    CONNECTOR_IMPLEMENTATION = "TAIGA"

    def get_artifact_types(self) -> List[str]:
        return ["task", "userstory", "epic", "project"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {"Authorization": f"Bearer {config.get('token')}"}

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/projects"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/tasks/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        project_slug = config.get("project_slug")
        if project_slug:
            return f"{self.BASE_URL}/projects/by_slug/{project_slug}/tasks"
        return f"{self.BASE_URL}/tasks"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        project_slug = config.get("project_slug")
        if project_slug:
            return {"status__is_closed": filter_params.get("status", "open")}
        return {"project": config.get("project")}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""