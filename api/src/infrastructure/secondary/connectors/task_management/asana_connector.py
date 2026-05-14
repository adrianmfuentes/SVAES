from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    BearerAuthMixin,
)


class AsanaConnector(BaseHttpConnector, BearerAuthMixin):
    BASE_URL = "https://app.asana.com/api/1.0"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "ASANA"

    def get_artifact_types(self) -> List[str]:
        return ["task", "project", "section"]

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/users/me"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/tasks/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return {"opt_fields": "name,status,assignee,created_at,modified_at"}

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        project_gid = config.get("project_gid")
        if project_gid:
            return f"{self.BASE_URL}/projects/{project_gid}/tasks"
        return f"{self.BASE_URL}/tasks/search"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        project_gid = config.get("project_gid")
        if project_gid:
            return {"opt_fields": "name,status,assignee,created_at,modified_at"}
        return {"workspace": config.get("workspace"), "count": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "data"