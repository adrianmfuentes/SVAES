from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class ClickUpConnector(BaseHttpConnector):
    BASE_URL = "https://api.clickup.com/api/v2"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "CLICKUP"

    def get_artifact_types(self) -> List[str]:
        return ["task", "list", "folder", "space", "goal"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"{config.get('token')}",
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/team"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/task/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Expose each ClickUp custom field as a flat top-level key using its own
        # name, so any field a user creates in ClickUp (e.g. "planned_tasks") can
        # be referenced directly by rule params without connector-side hardcoding.
        for field in data.get("custom_fields") or []:
            name = field.get("name")
            if name:
                data[name] = field.get("value")
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return self._normalize(response.json())

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        list_id = config.get("list_id")
        if list_id:
            return f"{self._get_base_url(config)}/list/{list_id}/task"
        team_id = config.get("team_id")
        return f"{self._get_base_url(config)}/team/{team_id}/task"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        list_id = config.get("list_id")
        params: Dict[str, Any] = {"subtasks": "false"} if list_id else {"include_subtasks": "false"}
        if filter_params.get("query_text"):
            params["query"] = filter_params["query_text"]
        return params

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "tasks"