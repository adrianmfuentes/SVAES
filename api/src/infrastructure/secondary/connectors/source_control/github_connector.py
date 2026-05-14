from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector

APPLICATION_JSON_VENDOR = "application/vnd.github+json"

class GitHubConnector(IConnector):
    BASE_URL = "https://api.github.com"

    @property
    def connector_type(self) -> str:
        return "REPO_CODIGO"

    @property
    def connector_implementation(self) -> str:
        return "GITHUB"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "GitHub",
            "version": "1.0",
            "artifact_types": ["pull_request", "commit", "release", "workflow_run"],
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = config.get("token")
            headers = {
                "Accept": APPLICATION_JSON_VENDOR,
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            response = await client.get(f"{self.BASE_URL}/user", headers=headers)
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = config.get("token")
            headers = {
                "Accept": APPLICATION_JSON_VENDOR,
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            owner, repo, issue_number = ref.split("/")
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{issue_number}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = config.get("token")
            owner = config.get("owner")
            repo = config.get("repo")
            headers = {
                "Accept": APPLICATION_JSON_VENDOR,
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            if owner and repo:
                response = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                    headers=headers,
                    params={"state": filter_params.get("state", "open"), "per_page": 50},
                )
            else:
                response = await client.get(
                    f"{self.BASE_URL}/user/pulls",
                    headers=headers,
                    params={"state": filter_params.get("state", "open"), "per_page": 50},
                )
            response.raise_for_status()
            return response.json()