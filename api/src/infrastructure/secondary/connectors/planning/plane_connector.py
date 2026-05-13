from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class PlaneConnector(IConnector):
    BASE_URL = "https://api.plane.io/api/v1"

    @property
    def connector_type(self) -> str:
        return "HERRAMIENTA_PLANIFICACION"

    @property
    def connector_implementation(self) -> str:
        return "PLANE"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Plane",
            "version": "1.0",
            "artifact_types": ["issue", "cycle", "module", "project"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "x-api-key": config.get("api_key", ""),
            "x-api-host": config.get("instance_url", ""),
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            workspace = config.get("workspace")
            response = await client.get(
                f"{self.BASE_URL}/workspaces/{workspace}/projects",
                headers=self._build_headers(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            workspace = config.get("workspace")
            response = await client.get(
                f"{self.BASE_URL}/workspaces/{workspace}/issues/{ref}",
                headers=self._build_headers(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            workspace = config.get("workspace")
            project = config.get("project")
            if project:
                response = await client.get(
                    f"{self.BASE_URL}/workspaces/{workspace}/projects/{project}/issues",
                    headers=self._build_headers(config),
                    params={"cycle": filter_params.get("cycle")},
                )
            else:
                response = await client.get(
                    f"{self.BASE_URL}/workspaces/{workspace}/issues",
                    headers=self._build_headers(config),
                )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])