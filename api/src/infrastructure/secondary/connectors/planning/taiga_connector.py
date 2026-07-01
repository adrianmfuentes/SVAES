from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class TaigaConnector(BaseHttpConnector):
    BASE_URL = "https://api.taiga.io/api/v1"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "TAIGA"

    def get_artifact_types(self) -> List[str]:
        return ["task", "userstory", "epic", "project"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {"Authorization": f"Bearer {config.get('token')}"}

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/projects"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/tasks/{ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Taiga's "status" is just the numeric status ID (FK), not a readable
        # value - the API includes the human-readable name in "status_extra_info".
        # Flatten it to a flat "status" string so rules like RV-03 can read it
        # the same way as every other GESTOR_TAREAS connector.
        status_extra = data.get("status_extra_info") or {}
        if isinstance(status_extra, dict) and status_extra.get("name"):
            data["status"] = status_extra["name"]
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return self._normalize(response.json())

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/tasks"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        project_id = config.get("project")
        return {"project": project_id} if project_id else None

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""