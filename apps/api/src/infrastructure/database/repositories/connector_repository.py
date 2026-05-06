from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from domain.entities.connector_instance import ConnectorInstance, ConnectorStatus
from domain.ports.i_connector_repository import IConnectorRepository
from infrastructure.database.models.connector_instance import ConnectorInstanceModel


class SqlConnectorRepository(IConnectorRepository):
    """Async SQLAlchemy adapter for IConnectorRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, connector: ConnectorInstance) -> ConnectorInstance:
        model = await self.session.get(ConnectorInstanceModel, connector.id)
        if model is None:
            model = ConnectorInstanceModel(
                id=connector.id,
                organization_id=connector.organization_id,
                connector_type=connector.connector_type,
                name=connector.connector_type,
                config_encrypted=connector.encrypted_credentials,
                status=connector.status.value,
            )
            self.session.add(model)
        else:
            model.config_encrypted = connector.encrypted_credentials
            model.status = connector.status.value
        await self.session.flush()
        return connector

    async def get_by_id(self, instance_id: UUID) -> Optional[ConnectorInstance]:
        model = await self.session.get(ConnectorInstanceModel, instance_id)
        return self._to_entity(model) if model else None

    async def list_by_organization(self, organization_id: UUID, active_only: bool = True) -> List[ConnectorInstance]:
        query = select(ConnectorInstanceModel).where(
            ConnectorInstanceModel.organization_id == organization_id
        )
        if active_only:
            query = query.where(ConnectorInstanceModel.status == "ACTIVO")
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: ConnectorInstanceModel) -> ConnectorInstance:
        return ConnectorInstance(
            id=model.id,
            organization_id=model.organization_id,
            connector_type=model.connector_type,
            encrypted_credentials=model.config_encrypted or b"",
            status=ConnectorStatus(model.status),
            created_at=model.created_at,
            updated_at=model.created_at,
        )
