from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class ClickUpConnector(BaseHttpConnector):
    BASE_URL = "https://api.clickup.com/api/v2"
    CONNECTOR_TYPE = "HERRAMIENTA_PLANIFICACION"
    CONNECTOR_IMPLEMENTATION = "CLICKUP"

    def get_artifact_types(self) -> List[str]:
        return ["task", "list", "folder", "space", "goal"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"{config.get('token')}",
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        team_id = config.get("team_id")
        return f"{self.BASE_URL}/team/{team_id}/goals"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/task/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        list_id = config.get("list_id")
        if list_id:
            return f"{self.BASE_URL}/list/{list_id}/task"
        team_id = config.get("team_id")
        return f"{self.BASE_URL}/team/{team_id}/task"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        list_id = config.get("list_id")
        if list_id:
            return {"subtasks": "false"}
        return {"include_subtasks": "false"}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "tasks"