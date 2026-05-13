from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class ClickUpConnector(IConnector):
    BASE_URL = "https://api.clickup.com/api/v2"

    @property
    def connector_type(self) -> str:
        return "HERRAMIENTA_PLANIFICACION"

    @property
    def connector_implementation(self) -> str:
        return "CLICKUP"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "ClickUp",
            "version": "1.0",
            "artifact_types": ["task", "list", "folder", "space", "goal"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"{config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            team_id = config.get("team_id")
            response = await client.get(
                f"{self.BASE_URL}/team/{team_id}/goals",
                headers=self._build_headers(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/task/{ref}",
                headers=self._build_headers(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            list_id = config.get("list_id")
            if list_id:
                response = await client.get(
                    f"{self.BASE_URL}/list/{list_id}/task",
                    headers=self._build_headers(config),
                    params={"subtasks": "false"},
                )
            else:
                team_id = config.get("team_id")
                response = await client.get(
                    f"{self.BASE_URL}/team/{team_id}/task",
                    headers=self._build_headers(config),
                    params={"include_subtasks": "false"},
                )
            response.raise_for_status()
            data = response.json()
            return data.get("tasks", [])