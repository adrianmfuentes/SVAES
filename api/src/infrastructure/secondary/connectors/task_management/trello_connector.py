from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class TrelloConnector(IConnector):
    BASE_URL = "https://api.trello.com/1"

    @property
    def connector_type(self) -> str:
        return "GESTOR_TAREAS"

    @property
    def connector_implementation(self) -> str:
        return "TRELLO"

    def get_connector_type(self) -> str:
        return "GESTOR_TAREAS"

    def get_connector_implementation(self) -> str:
        return "TRELLO"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Trello",
            "version": "1.0",
            "artifact_types": ["card", "list", "board"],
        }

    def _get_base_url(self, config: Dict[str, Any]) -> str:
        base = (config.get("base_url") or self.BASE_URL).rstrip("/")
        if "/1/" not in base and not base.endswith("/1"):
            base += "/1"
        return base

    def _build_auth_params(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "key": config.get("api_key", ""),
            "token": config.get("token", ""),
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {**self._build_auth_params(config)}
            response = await client.get(
                f"{self._get_base_url(config)}/members/me",
                params=params,
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {**self._build_auth_params(config)}
            response = await client.get(
                f"{self._get_base_url(config)}/cards/{ref}",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                **self._build_auth_params(config),
                "cards": "open",
                "card_fields": "id,name,idList,shortUrl,dateLastActivity",
            }
            board_id = config.get("board_id")
            if board_id:
                response = await client.get(
                    f"{self._get_base_url(config)}/boards/{board_id}/cards",
                    params=params,
                )
            else:
                response = await client.get(
                    f"{self._get_base_url(config)}/members/me/cards",
                    params=params,
                )
            response.raise_for_status()
            return response.json()