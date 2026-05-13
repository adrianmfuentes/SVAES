from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class MiroConnector(IConnector):
    BASE_URL = "https://api.miro.com/v1"

    @property
    def connector_type(self) -> str:
        return "HERRAMIENTA_PLANIFICACION"

    @property
    def connector_implementation(self) -> str:
        return "MIRO"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Miro",
            "version": "1.0",
            "artifact_types": ["board", "card", "sticky_note"],
        }

    def _build_auth(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/boards",
                headers=self._build_auth(config),
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/boards/{ref}",
                headers=self._build_auth(config),
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/boards",
                headers=self._build_auth(config),
                params={"limit": 50},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])