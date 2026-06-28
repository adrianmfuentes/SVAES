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
        return f"{self.BASE_URL}/user"

    def _get_fetch_url(self, ref: str, config: Dict[str, Any]) -> str:
        parts = ref.split("/", 2)
        if len(parts) == 3:
            owner, repo, pr_id = parts
        else:
            owner = config.get("owner", "")
            repo = config.get("repo", "")
            pr_id = parts[-1]
        return f"{self.BASE_URL}/repositories/{owner}/{repo}/pullrequests/{pr_id}"

    def _get_fetch_params(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        return None

    def _get_list_url(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> str:
        owner = config.get("owner")
        repo = config.get("repo")
        if owner and repo:
            return f"{self.BASE_URL}/repositories/{owner}/{repo}/pullrequests"
        return f"{self.BASE_URL}/user/pullrequests"

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