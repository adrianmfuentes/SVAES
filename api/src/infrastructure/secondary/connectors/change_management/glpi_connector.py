from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class GLPiConnector(IConnector):
    BASE_URL = "https://example.com/apirest.php"

    @property
    def connector_type(self) -> str:
        return "GESTION_CAMBIOS"

    @property
    def connector_implementation(self) -> str:
        return "GLPI"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "GLPI",
            "version": "1.0",
            "artifact_types": ["ticket", "change", "problem"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "App-Token": config.get("app_token", ""),
            "Authorization": f"user_token {config.get('user_token')}",
            "Content-Type": "application/json",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/init",
                headers=self._build_headers(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/Ticket/{ref}",
                headers=self._build_headers(config),
                params={"show": "1"},
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            item_type = filter_params.get("item_type", "Ticket")
            response = await client.get(
                f"{base_url}/{item_type}",
                headers=self._build_headers(config),
                params={"range": f"0-{filter_params.get('limit', 50)}"},
            )
            response.raise_for_status()
            return response.json()

    async def list_changes(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/Change",
                headers=self._build_headers(config),
                params={"range": "0-50"},
            )
            response.raise_for_status()
            return response.json()