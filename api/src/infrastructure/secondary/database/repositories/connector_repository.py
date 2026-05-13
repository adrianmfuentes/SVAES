from sqlalchemy.future import select
from typing import Optional, List
import uuid
from datetime import datetime
from application.ports.output.i_connector_repository import IConnectorRepository
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from infrastructure.secondary.database.models.connector_model import ConnectorInstanceModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlConnectorRepository(IConnectorRepository):
    async def save(self, connector: ConnectorInstance) -> ConnectorInstance:
        session = await get_async_session().__anext__()

        try:
            connector_model = ConnectorInstanceModel(
                id=connector.id,
                organization_id=connector.organization_id,
                connector_type=connector.connector_type,
                name=connector.name,
                encrypted_credentials=connector.encrypted_credentials,
                status=connector.status.value,
                created_at=connector.created_at,
                updated_at=connector.updated_at,
                last_tested_at=connector.last_tested_at,
            )
            session.add(connector_model)
            await session.commit()
            await session.refresh(connector_model)

            return ConnectorInstance(
                id=connector_model.id,
                organization_id=connector_model.organization_id,
                connector_type=connector_model.connector_type,
                name=connector_model.name,
                encrypted_credentials=connector_model.encrypted_credentials,
                status=ConnectorStatus(connector_model.status),
                created_at=connector_model.created_at,
                updated_at=connector_model.updated_at,
                last_tested_at=connector_model.last_tested_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_id(self, instance_id: uuid.UUID) -> Optional[ConnectorInstance]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(ConnectorInstanceModel).where(ConnectorInstanceModel.id == instance_id))
            connector_row = result.scalar_one_or_none()
            if not connector_row:
                return None

            return ConnectorInstance(
                id=connector_row.id,
                organization_id=connector_row.organization_id,
                connector_type=connector_row.connector_type,
                name=connector_row.name,
                encrypted_credentials=connector_row.encrypted_credentials,
                status=ConnectorStatus(connector_row.status),
                created_at=connector_row.created_at,
                updated_at=connector_row.updated_at,
                last_tested_at=connector_row.last_tested_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_by_organization(
        self, organization_id: uuid.UUID, active_only: bool = True, skip: int = 0, limit: int = 50
    ) -> List[ConnectorInstance]:
        session = await get_async_session().__anext__()

        try:
            query = select(ConnectorInstanceModel).where(ConnectorInstanceModel.organization_id == organization_id)
            if active_only:
                query = query.where(ConnectorInstanceModel.status == ConnectorStatus.ACTIVO.value)
            query = query.offset(skip).limit(limit)

            result = await session.execute(query)
            connector_rows = result.scalars().all()

            return [
                ConnectorInstance(
                    id=row.id,
                    organization_id=row.organization_id,
                    connector_type=row.connector_type,
                    name=row.name,
                    encrypted_credentials=row.encrypted_credentials,
                    status=ConnectorStatus(row.status),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    last_tested_at=row.last_tested_at,
                )
                for row in connector_rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_active(self, organization_id: uuid.UUID) -> List[ConnectorInstance]:
        return await self.list_by_organization(organization_id, active_only=True, skip=0, limit=100)

    async def update(self, connector: ConnectorInstance) -> ConnectorInstance:
        session = await get_async_session().__anext__()

        try:
            connector_model = await session.get(ConnectorInstanceModel, connector.id)
            if not connector_model:
                raise ValueError("Connector not found")

            connector_model.connector_type = connector.connector_type
            connector_model.name = connector.name
            connector_model.encrypted_credentials = connector.encrypted_credentials
            connector_model.status = connector.status.value
            connector_model.updated_at = datetime.utcnow()
            connector_model.last_tested_at = connector.last_tested_at

            await session.commit()
            await session.refresh(connector_model)

            return ConnectorInstance(
                id=connector_model.id,
                organization_id=connector_model.organization_id,
                connector_type=connector_model.connector_type,
                name=connector_model.name,
                encrypted_credentials=connector_model.encrypted_credentials,
                status=ConnectorStatus(connector_model.status),
                created_at=connector_model.created_at,
                updated_at=connector_model.updated_at,
                last_tested_at=connector_model.last_tested_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete(self, connector_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()

        try:
            connector_model = await session.get(ConnectorInstanceModel, connector_id)
            if not connector_model:
                raise ValueError("Connector not found")

            await session.delete(connector_model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()