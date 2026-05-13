from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class JiraServiceManagementConnector(IConnector):
    BASE_URL = "https://api.atlassian.com"

    @property
    def connector_type(self) -> str:
        return "GESTION_CAMBIOS"

    @property
    def connector_implementation(self) -> str:
        return "JIRA_SM"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Jira Service Management",
            "version": "1.0",
            "artifact_types": ["request", "request_type", "approval"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "email": config.get("email"),
            "api_token": config.get("api_token"),
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        return config.get("base_url", self.BASE_URL)

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = self._get_base_url(config)
            site_id = config.get("site_id")
            auth = self._build_auth(config)
            response = await client.get(
                f"{base_url}/rest/servicedesk/1/servicedesk",
                headers={
                    "Accept": "application/json",
                    "email": auth["email"],
                    "api_token": auth["api_token"],
                },
                params={"siteId": site_id} if site_id else None,
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = self._get_base_url(config)
            auth = self._build_auth(config)
            response = await client.get(
                f"{base_url}/rest/servicedesk/1/request/{ref}",
                headers={
                    "Accept": "application/json",
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
            service_desk_id = config.get("service_desk_id")
            if service_desk_id:
                response = await client.get(
                    f"{base_url}/rest/servicedesk/1/servicedesk/{service_desk_id}/request",
                    headers={
                        "Accept": "application/json",
                        "email": auth["email"],
                        "api_token": auth["api_token"],
                    },
                    params={"requestType": filter_params.get("request_type"), "limit": 50},
                )
            else:
                response = await client.get(
                    f"{base_url}/rest/servicedesk/1/request",
                    headers={
                        "Accept": "application/json",
                        "email": auth["email"],
                        "api_token": auth["api_token"],
                    },
                    params={"limit": 50},
                )
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])