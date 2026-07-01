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
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if "/api/" not in base:
            base += "/api/v1"
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
        # /git/commits/{sha} resolves a commit sha (full or short), a branch name or a tag name.
        return f"{base}/git/commits/{sub_ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # RV-09 reads flat "link"/"branch"/"accessible" keys, but Gitea's real
        # PR/commit JSON (mirroring GitHub's API shape) uses "html_url" and a
        # nested "head.ref" - flatten them so the rule can actually validate
        # something instead of silently skipping every artifact.
        if data.get("html_url"):
            data["link"] = data["html_url"]
        head = data.get("head") or {}
        if isinstance(head, dict) and head.get("ref"):
            data["branch"] = head["ref"]
        data["accessible"] = True
        return data

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = self._get_fetch_url(ref, config)
        response = await self._get(url, config, self._get_fetch_params(config))
        response.raise_for_status()
        return self._normalize(response.json())

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