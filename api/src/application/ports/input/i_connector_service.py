from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus

class IConnectorService(ABC):
    @abstractmethod
    async def register_connector(
        self,
        organization_id: UUID,
        connector_type: str,
        connector_implementation: str,
        name: str,
        config: dict,
        requested_by: UUID,
    ) -> ConnectorInstance:
        pass

    @abstractmethod
    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        requested_by: Optional[UUID] = None,
    ) -> ConnectorInstance:
        pass

    @abstractmethod
    async def test_connector_connection(self, connector_id: UUID, requested_by: UUID) -> ConnectorInstance:
        pass

    @abstractmethod
    async def list_connectors(
        self,
        organization_id: UUID,
        active_only: bool = True,
    ) -> List[ConnectorInstance]:
        pass

    @abstractmethod
    async def get_connector(self, connector_id: UUID) -> Optional[ConnectorInstance]:
        pass

    @abstractmethod
    async def delete_connector(self, connector_id: UUID, requested_by: UUID) -> None:
        pass

    @abstractmethod
    async def toggle_connector_status(
        self, connector_id: UUID, status: ConnectorStatus, requested_by: UUID
    ) -> ConnectorInstance:
        pass

    @abstractmethod
    async def browse_connector_items(
        self, connector_id: UUID, query: str = ""
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def verify_artifact_ref(
        self, connector_id: UUID, external_ref: str, organization_id: Optional[UUID] = None
    ) -> None:
        """Raises ValidationError if external_ref does not exist in the connector,
        or if organization_id is given and does not match the connector's organization."""
        pass

    @abstractmethod
    async def configure_webhook(
        self,
        connector_id: UUID,
        enabled: bool,
        requested_by: UUID,
        regenerate_secret: bool = False,
    ) -> Tuple[ConnectorInstance, Optional[str]]:
        """Enables/disables inbound webhook auto-verification for a source-control
        connector. Returns (connector, plaintext_secret) - the plaintext secret is
        only returned the call that generates it (first enable, or explicit
        regenerate_secret=True), since only its encrypted form is persisted."""
        pass