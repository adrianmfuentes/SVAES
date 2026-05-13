from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class AsanaConnector(IConnector):
    BASE_URL = "https://app.asana.com/api/1.0"

    @property
    def connector_type(self) -> str:
        return "GESTOR_TAREAS"

    @property
    def connector_implementation(self) -> str:
        return "ASANA"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Asana",
            "version": "1.0",
            "artifact_types": ["task", "project", "section"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/users/me",
                headers=self._build_headers(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/tasks/{ref}",
                headers=self._build_headers(config),
                params={"opt_fields": "name,status,assignee,created_at,modified_at"},
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            project_gid = config.get("project_gid")
            if project_gid:
                response = await client.get(
                    f"{self.BASE_URL}/projects/{project_gid}/tasks",
                    headers=self._build_headers(config),
                    params={"opt_fields": "name,status,assignee,created_at,modified_at"},
                )
            else:
                response = await client.get(
                    f"{self.BASE_URL}/tasks/search",
                    headers=self._build_headers(config),
                    params={"workspace": config.get("workspace"), "count": 50},
                )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])