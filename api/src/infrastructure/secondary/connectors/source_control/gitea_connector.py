from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class GiteaConnector(BaseHttpConnector):
    BASE_URL = "https://gitea.com/api/v1"
    CONNECTOR_TYPE = "REPO_CODIGO"
    CONNECTOR_IMPLEMENTATION = "GITEA"

    def get_artifact_types(self) -> List[str]:
        return ["pull_request", "release", "commit"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"token {config.get('token')}",
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        return config.get("base_url", self.BASE_URL)

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/user"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        parts = ref.split("/", 2)
        if len(parts) == 3:
            owner, repo, pr_number = parts
        else:
            owner = config.get("owner", "")
            repo = config.get("repo", "")
            pr_number = parts[-1]
        return f"{self._get_base_url(config)}/repos/{owner}/{repo}/pulls/{pr_number}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        owner = config.get("owner")
        repo = config.get("repo")
        if owner and repo:
            return f"{self._get_base_url(config)}/repos/{owner}/{repo}/pulls"
        return f"{self._get_base_url(config)}/user/repos"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        owner = config.get("owner")
        repo = config.get("repo")
        if owner and repo:
            return {"state": filter_params.get("state", "open"), "limit": 50}
        return {"limit": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""