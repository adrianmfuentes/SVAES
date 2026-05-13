from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class TaigaConnector(IConnector):
    BASE_URL = "https://api.taiga.io/api/v1"

    @property
    def connector_type(self) -> str:
        return "HERRAMIENTA_PLANIFICACION"

    @property
    def connector_implementation(self) -> str:
        return "TAIGA"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Taiga",
            "version": "1.0",
            "artifact_types": ["task", "userstory", "epic", "project"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/projects",
                headers=self._build_auth(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/tasks/{ref}",
                headers=self._build_auth(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            project_slug = config.get("project_slug")
            if project_slug:
                response = await client.get(
                    f"{self.BASE_URL}/projects/by_slug/{project_slug}/tasks",
                    headers=self._build_auth(config),
                    params={"status__is_closed": filter_params.get("status", "open")},
                )
            else:
                response = await client.get(
                    f"{self.BASE_URL}/tasks",
                    headers=self._build_auth(config),
                    params={"project": config.get("project")},
                )
            response.raise_for_status()
            return response.json()