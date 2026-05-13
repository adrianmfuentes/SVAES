from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class RedmineConnector(IConnector):
    BASE_URL = "https://example.com"

    @property
    def connector_type(self) -> str:
        return "GESTION_CAMBIOS"

    @property
    def connector_implementation(self) -> str:
        return "REDMINE"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Redmine",
            "version": "1.0",
            "artifact_types": ["issue", "project", "time_entry"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, Any]:
        api_key = config.get("api_key")
        return {
            "X-Redmine-API-Key": api_key,
            "Accept": "application/json",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/projects.xml",
                headers=self._build_auth(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/issues/{ref}.json",
                headers=self._build_auth(config),
                params={"include": "children,relations,changesets"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("issue", {})

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            project_id = config.get("project_id")
            params = {
                "limit": filter_params.get("limit", 50),
                "status_id": filter_params.get("status_id", "open"),
            }
            if project_id:
                params["project_id"] = project_id
            response = await client.get(
                f"{base_url}/issues.json",
                headers=self._build_auth(config),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("issues", [])