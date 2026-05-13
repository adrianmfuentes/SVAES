from typing import Any, Dict, List
import httpx
from application.ports.output.i_connector import IConnector


class WikiJsConnector(IConnector):
    BASE_URL = "http://localhost:3000"

    @property
    def connector_type(self) -> str:
        return "SISTEMA_DOCUMENTAL"

    @property
    def connector_implementation(self) -> str:
        return "WIKIJS"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Wiki.js",
            "version": "1.0",
            "artifact_types": ["page", "asset"],
        }

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {config.get('token')}",
        }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            response = await client.get(
                f"{base_url}/graphql",
                headers=self._build_headers(config),
                json={"query": "{ users { total } }"},
            )
            return response.status_code == 200

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            query = f'{{ page(location: "{{{{ path: \"{ref}\" }}}}") {{ id title content updatedAt }} }}'
            response = await client.post(
                f"{base_url}/graphql",
                headers=self._build_headers(config),
                json={"query": query},
            )
            response.raise_for_status()
            return response.json()

    async def list_artifacts(
        self, filter_params: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = config.get("base_url", self.BASE_URL)
            query = "{ pages(orderBy: [{ field: 'updatedAt', direction: DESC }], first: 50) { results { id title path updatedAt } } }"
            response = await client.post(
                f"{base_url}/graphql",
                headers=self._build_headers(config),
                json={"query": query},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("pages", {}).get("results", [])