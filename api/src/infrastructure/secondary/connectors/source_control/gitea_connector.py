from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class GiteaConnector(IConnector):
    BASE_URL = "https://gitea.com/api/v1"

    @property
    def connector_type(self) -> str:
        return "REPO_CODIGO"

    @property
    def connector_implementation(self) -> str:
        return "GITEA"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Gitea",
            "version": "1.0",
            "artifact_types": ["pull_request", "release", "commit"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"token {config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/user",
                headers=self._build_headers(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            owner, repo, pr_number = ref.split("/")
            response = await client.get(
                f"{base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._build_headers(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            owner = config.get("owner")
            repo = config.get("repo")
            if owner and repo:
                response = await client.get(
                    f"{base_url}/repos/{owner}/{repo}/pulls",
                    headers=self._build_headers(config),
                    params={"state": filter_params.get("state", "open"), "limit": 50},
                )
            else:
                response = await client.get(
                    f"{base_url}/user/repos",
                    headers=self._build_headers(config),
                    params={"limit": 50},
                )
            response.raise_for_status()
            return response.json()