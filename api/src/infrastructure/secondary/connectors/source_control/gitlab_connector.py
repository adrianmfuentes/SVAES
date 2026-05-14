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
        return f"{self.BASE_URL}/user"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        project_id, mr_iid = ref.split("/")
        return f"{self.BASE_URL}/projects/{project_id}/merge_requests/{mr_iid}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        project_id = config.get("project_id")
        if project_id:
            return f"{self.BASE_URL}/projects/{project_id}/merge_requests"
        return f"{self.BASE_URL}/merge_requests"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {"state": filter_params.get("state", "opened"), "per_page": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""