from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime, timezone
from application.ports.output.i_connector_repository import IConnectorRepository
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from infrastructure.secondary.database.models.connector_model import ConnectorInstanceModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


def _model_to_entity(row: ConnectorInstanceModel) -> ConnectorInstance:
    return ConnectorInstance(
        id=cast(uuid.UUID, row.id),
        organization_id=cast(uuid.UUID, row.organization_id),
        connector_type=cast(str, row.connector_type),
        connector_implementation=cast(str, row.connector_implementation),
        name=cast(str, row.name),
        encrypted_credentials=cast(bytes, row.config_encrypted),
        status=ConnectorStatus(row.status),
        created_at=cast(datetime, row.created_at),
        updated_at=cast(datetime | None, row.updated_at),
        last_tested_at=cast(datetime | None, row.last_tested_at),
    )


class SqlConnectorRepository(IConnectorRepository):
    async def save(self, connector: ConnectorInstance) -> ConnectorInstance:
        async with AsyncSessionLocal() as session:
            connector_model = ConnectorInstanceModel(
                id=connector.id,
                organization_id=connector.organization_id,
                connector_type=connector.connector_type,
                connector_implementation=connector.connector_implementation,
                name=connector.name,
                config_encrypted=connector.encrypted_credentials,
                status=connector.status.value if hasattr(connector.status, 'value') else connector.status,
                created_at=connector.created_at,
                updated_at=connector.updated_at,
                last_tested_at=connector.last_tested_at,
            )
            session.add(connector_model)
            await session.commit()
            await session.refresh(connector_model)

            return _model_to_entity(connector_model)

    async def get_by_id(self, instance_id: uuid.UUID) -> Optional[ConnectorInstance]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ConnectorInstanceModel).where(ConnectorInstanceModel.id == instance_id))
            connector_row = result.scalar_one_or_none()
            if not connector_row:
                return None

            return _model_to_entity(connector_row)

    async def list_by_organization(
        self, organization_id: uuid.UUID, active_only: bool = True, skip: int = 0, limit: int = 50
    ) -> List[ConnectorInstance]:
        async with AsyncSessionLocal() as session:
            query = select(ConnectorInstanceModel).where(ConnectorInstanceModel.organization_id == organization_id)
            if active_only:
                query = query.where(ConnectorInstanceModel.status == ConnectorStatus.ACTIVO)
            query = query.offset(skip).limit(limit)

            result = await session.execute(query)
            connector_rows = result.scalars().all()

            return [_model_to_entity(row) for row in connector_rows]

    async def list_active(self, organization_id: uuid.UUID) -> List[ConnectorInstance]:
        return await self.list_by_organization(organization_id, active_only=True, skip=0, limit=100)

    async def update(self, connector: ConnectorInstance) -> ConnectorInstance:
        async with AsyncSessionLocal() as session:
            connector_model = await session.get(ConnectorInstanceModel, connector.id)
            if not connector_model:
                raise ValueError("Connector not found")

            connector_model.connector_type = connector.connector_type  # pyright: ignore[reportAttributeAccessIssue]
            connector_model.connector_implementation = connector.connector_implementation  # pyright: ignore[reportAttributeAccessIssue]
            connector_model.name = connector.name  # pyright: ignore[reportAttributeAccessIssue]
            connector_model.config_encrypted = connector.encrypted_credentials  # pyright: ignore[reportAttributeAccessIssue]
            connector_model.status = connector.status.value if hasattr(connector.status, 'value') else connector.status  # pyright: ignore[reportAttributeAccessIssue]
            connector_model.updated_at = datetime.now(timezone.utc)
            connector_model.last_tested_at = connector.last_tested_at  # pyright: ignore[reportAttributeAccessIssue]

            await session.commit()
            await session.refresh(connector_model)

            return _model_to_entity(connector_model)

    async def delete(self, connector_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            connector_model = await session.get(ConnectorInstanceModel, connector_id)
            if not connector_model:
                raise ValueError("Connector not found")

            await session.delete(connector_model)
            await session.commit()