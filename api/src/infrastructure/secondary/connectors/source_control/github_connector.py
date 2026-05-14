from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import (
    BaseHttpConnector,
    BearerAuthMixin,
)


class GitHubConnector(BaseHttpConnector, BearerAuthMixin):
    BASE_URL = "https://api.github.com"
    CONNECTOR_TYPE = "REPO_CODIGO"
    CONNECTOR_IMPLEMENTATION = "GITHUB"

    def get_artifact_types(self) -> List[str]:
        return ["pull_request", "commit", "release", "workflow_run"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {config.get('token')}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self.BASE_URL}/user"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        owner, repo, issue_number = ref.split("/")
        return f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{issue_number}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        owner = config.get("owner")
        repo = config.get("repo")
        if owner and repo:
            return f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        return f"{self.BASE_URL}/user/pulls"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {"state": filter_params.get("state", "open"), "per_page": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""