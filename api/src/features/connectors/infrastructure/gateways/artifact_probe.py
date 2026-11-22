from typing import Any

import httpx

from features.connectors.application.ports.i_connector import IConnector


class HttpConnectorArtifactProbe:
    async def exists(self, connector: IConnector, ref: str, config: dict[str, Any]) -> bool:
        try:
            await connector.fetch_artifact(ref, config)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return False
            raise
        return True
