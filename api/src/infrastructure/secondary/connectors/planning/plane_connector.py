from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class PlaneConnector(BaseHttpConnector):
    BASE_URL = "https://api.plane.so/api/v1"
    CONNECTOR_TYPE = "GESTOR_TAREAS"
    CONNECTOR_IMPLEMENTATION = "PLANE"

    def get_artifact_types(self) -> List[str]:
        return ["issue", "cycle", "module", "project"]

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        instance_url = (config.get("instance_url") or "").rstrip("/")
        if instance_url:
            return f"{instance_url}/api/v1"
        return self.BASE_URL

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "X-API-Key": config.get("api_key", ""),
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        workspace = config.get("workspace")
        return f"{self._get_base_url(config)}/workspaces/{workspace}/projects/"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        workspace = config.get("workspace")
        return f"{self._get_base_url(config)}/workspaces/{workspace}/issues/{ref}/"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Plane's "state" field is just the state's UUID, not a readable value -
        # the human-readable name/group is under the expanded "state_detail".
        # Flatten it to a flat "status" string so rules like RV-03 can read it
        # the same way as every other GESTOR_TAREAS connector.
        state_detail = data.get("state_detail") or {}
        if isinstance(state_detail, dict) and state_detail.get("name"):
            data["status"] = state_detail["name"]
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return self._normalize(response.json())

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        workspace = config.get("workspace")
        project = config.get("project")
        if project:
            return f"{self._get_base_url(config)}/workspaces/{workspace}/projects/{project}/issues/"
        return f"{self._get_base_url(config)}/workspaces/{workspace}/issues/"

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