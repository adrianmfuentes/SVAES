from typing import Any, Dict, List
from infrastructure.secondary.connectors.base_http_connector import BaseHttpConnector


class BitbucketConnector(BaseHttpConnector):
    BASE_URL = "https://api.bitbucket.org/2.0"
    CONNECTOR_TYPE = "REPO_CODIGO"
    CONNECTOR_IMPLEMENTATION = "BITBUCKET"

    def get_artifact_types(self) -> List[str]:
        return ["pullrequest", "commit", "pipeline"]

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {"Authorization": f"Bearer {config.get('token')}"}

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
        base = f"{self._get_base_url(config)}/repositories/{owner}/{repo}"
        if sub_ref.isdigit():
            return f"{base}/pullrequests/{sub_ref}"
        # /commit/{revision} resolves a commit hash (full or short), a branch name or a tag name.
        return f"{base}/commit/{sub_ref}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # RV-09 reads flat "link"/"branch"/"accessible" keys, but Bitbucket's
        # real PR JSON nests them under "links.html.href" and
        # "source.branch.name" - flatten them so the rule can actually
        # validate something instead of silently skipping every artifact.
        html_link = (data.get("links") or {}).get("html") or {}
        if isinstance(html_link, dict) and html_link.get("href"):
            data["link"] = html_link["href"]
        source_branch = ((data.get("source") or {}).get("branch") or {})
        if isinstance(source_branch, dict) and source_branch.get("name"):
            data["branch"] = source_branch["name"]
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
            return f"{self._get_base_url(config)}/repositories/{owner}/{repo}/pullrequests"
        return f"{self._get_base_url(config)}/user/pullrequests"

    def _get_list_params(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return {"state": filter_params.get("state", "OPEN"), "pagelen": 50}

    def _get_list_json(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        return None

    def _get_results_key(self) -> str:
        return "values"