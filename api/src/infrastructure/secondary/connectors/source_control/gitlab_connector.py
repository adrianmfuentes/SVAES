from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class GitLabConnector(IConnector):
    BASE_URL = "https://gitlab.com/api/v4"

    @property
    def connector_type(self) -> str:
        return "REPO_CODIGO"

    @property
    def connector_implementation(self) -> str:
        return "GITLAB"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "GitLab",
            "version": "1.0",
            "artifact_types": ["merge_request", "commit", "pipeline", "release"],
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = config.get("token")
            headers = {"Authorization": f"Bearer {token}"}

            response = await client.get(f"{self.BASE_URL}/user", headers=headers)
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = config.get("token")
            headers = {"Authorization": f"Bearer {token}"}

            project_id, mr_iid = ref.split("/")
            response = await client.get(
                f"{self.BASE_URL}/projects/{project_id}/merge_requests/{mr_iid}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = config.get("token")
            project_id = config.get("project_id")
            headers = {"Authorization": f"Bearer {token}"}

            if project_id:
                response = await client.get(
                    f"{self.BASE_URL}/projects/{project_id}/merge_requests",
                    headers=headers,
                    params={
                        "state": filter_params.get("state", "opened"),
                        "per_page": 50,
                    },
                )
            else:
                response = await client.get(
                    f"{self.BASE_URL}/merge_requests",
                    headers=headers,
                    params={
                        "state": filter_params.get("state", "opened"),
                        "per_page": 50,
                    },
                )
            response.raise_for_status()
            return response.json()