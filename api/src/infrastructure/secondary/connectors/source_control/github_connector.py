from typing import Any, Dict, List
from urllib.parse import urlparse

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

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if "api.github.com" not in base and "/api/" not in base:
            parsed = urlparse(base)
            if parsed.hostname == "github.com":
                base = base.replace("github.com", "api.github.com", 1)
            else:
                base += "/api/v3"
        return base

    def _get_health_url(self, config: Dict[str, Any]) -> str:
        return f"{self._get_base_url(config)}/user"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        parts = ref.split("/", 2)
        if len(parts) == 3:
            owner, repo, sub_ref = parts
        else:
            owner = config.get("owner", "")
            repo = config.get("repo", "")
            sub_ref = parts[-1]
        base = f"{self._get_base_url(config)}/repos/{owner}/{repo}"
        if sub_ref.isdigit():
            return f"{base}/pulls/{sub_ref}"
        # /commits/{ref} resolves a commit SHA (full or short), a branch name or a tag name.
        return f"{base}/commits/{sub_ref}"

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
        return {"state": filter_params.get("state", "open"), "per_page": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return ""