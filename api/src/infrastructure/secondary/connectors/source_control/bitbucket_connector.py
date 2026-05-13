from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class BitbucketConnector(IConnector):
    BASE_URL = "https://api.bitbucket.org/2.0"

    @property
    def connector_type(self) -> str:
        return "REPO_CODIGO"

    @property
    def connector_implementation(self) -> str:
        return "BITBUCKET"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Bitbucket",
            "version": "1.0",
            "artifact_types": ["pullrequest", "commit", "pipeline"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> str:
        return f"Bearer {config.get('token')}"

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/user",
                headers={"Authorization": self._build_auth(config)},
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            owner, repo, pr_id = ref.split("/")
            response = await client.get(
                f"{self.BASE_URL}/repositories/{owner}/{repo}/pullrequests/{pr_id}",
                headers={"Authorization": self._build_auth(config)},
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            owner = config.get("owner")
            repo = config.get("repo")
            if owner and repo:
                response = await client.get(
                    f"{self.BASE_URL}/repositories/{owner}/{repo}/pullrequests",
                    headers={"Authorization": self._build_auth(config)},
                    params={"state": filter_params.get("state", "OPEN"), "pagelen": 50},
                )
            else:
                response = await client.get(
                    f"{self.BASE_URL}/user/pullrequests",
                    headers={"Authorization": self._build_auth(config)},
                    params={"state": filter_params.get("state", "OPEN"), "pagelen": 50},
                )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])