from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector

APPLICATION_JSON = "application/json"

class JiraConnector(IConnector):
    BASE_URL = "https://api.atlassian.com"

    @property
    def connector_type(self) -> str:
        return "GESTOR_TAREAS"

    @property
    def connector_implementation(self) -> str:
        return "JIRA"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Jira",
            "version": "1.0",
            "artifact_types": ["issue", "project", "board"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, str]:
        # Ensure returned values are strings to match the declared return type
        email = config.get("email", "") or ""
        api_token = config.get("api_token", "") or ""
        return {"email": email, "api_token": api_token}

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        return config.get("base_url", self.BASE_URL)

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = self._get_base_url(config)
            cloud_id = config.get("cloud_id")
            auth = self._build_auth(config)

            response = await client.get(
                f"{base_url}/rest/api/3/myself",
                headers={
                    "Accept": APPLICATION_JSON,
                    "email": auth["email"],
                    "api_token": auth["api_token"],
                },
                params={"cloudId": cloud_id} if cloud_id else None,
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = self._get_base_url(config)
            auth = self._build_auth(config)

            response = await client.get(
                f"{base_url}/rest/api/3/issue/{ref}",
                headers={
                    "Accept": APPLICATION_JSON,
                    "email": auth["email"],
                    "api_token": auth["api_token"],
                },
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = self._get_base_url(config)
            auth = self._build_auth(config)
            jql = filter_params.get("jql", "updated >= -1d")
            max_results = filter_params.get("max_results", 50)

            response = await client.get(
                f"{base_url}/rest/api/3/search",
                headers={
                    "Accept": APPLICATION_JSON,
                    "email": auth["email"],
                    "api_token": auth["api_token"],
                },
                params={"jql": jql, "maxResults": max_results},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("issues", [])