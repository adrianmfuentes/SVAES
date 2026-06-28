from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    BearerAuthMixin,
)


class GitLabConnector(BaseHttpConnector, BearerAuthMixin):
    BASE_URL = "https://gitlab.com/api/v4"
    CONNECTOR_TYPE = "REPO_CODIGO"
    CONNECTOR_IMPLEMENTATION = "GITLAB"

    def get_artifact_types(self) -> List[str]:
        return ["merge_request", "commit", "pipeline", "release"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {"Authorization": f"Bearer {config.get('token')}"}

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/user"

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if "/api/" not in base:
            base += "/api/v4"
        return base

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        if "/" in ref:
            project_id, sub_ref = ref.split("/", 1)
        else:
            project_id = config.get("project_id", "")
            sub_ref = ref
        base = self._get_base_url(config)
        if sub_ref.isdigit():
            return f"{base}/projects/{project_id}/merge_requests/{sub_ref}"
        return f"{base}/projects/{project_id}/releases/{sub_ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        project_id = config.get("project_id")
        if project_id:
            return f"{self._get_base_url(config)}/projects/{project_id}/merge_requests"
        return f"{self._get_base_url(config)}/merge_requests"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        params: Dict[str, Any] = {"state": filter_params.get("state", "all"), "per_page": 50}
        if filter_params.get("search"):
            params["search"] = filter_params["search"]
        return params

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""