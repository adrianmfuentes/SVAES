from typing import Any, Protocol

from features.connectors.application.ports.i_connector import IConnector


class IConnectorArtifactProbe(Protocol):
    async def exists(self, connector: IConnector, ref: str, config: dict[str, Any]) -> bool: ...
