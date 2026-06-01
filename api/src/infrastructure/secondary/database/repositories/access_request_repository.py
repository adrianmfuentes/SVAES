from sqlalchemy.future import select
from typing import List, Optional, cast
import uuid
from datetime import datetime, timezone
from application.ports.output.i_access_request_repository import IAccessRequestRepository
from domain.entities.access_request import AccessRequest
from domain.enums import AccessRequestStatus
from infrastructure.secondary.database.models.access_request_model import AccessRequestModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlAccessRequestRepository(IAccessRequestRepository):
    def _model_to_entity(self, row: AccessRequestModel) -> AccessRequest:
        return AccessRequest(
            id=cast(uuid.UUID, row.id),
            requester_name=cast(str, row.requester_name),
            requester_email=cast(str, row.requester_email),
            organization_name=cast(str, row.organization_name),
            organization_description=cast(str | None, row.organization_description),
            slug_preview=cast(str | None, row.slug_preview),
            status=AccessRequestStatus(row.status),
            rejection_reason=cast(str | None, row.rejection_reason),
            reviewed_by=cast(uuid.UUID | None, row.reviewed_by),
            reviewed_at=cast(datetime | None, row.reviewed_at),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    async def create(self, access_request: AccessRequest) -> AccessRequest:
        async with AsyncSessionLocal() as session:
            model = AccessRequestModel(
                id=access_request.id,
                requester_name=access_request.requester_name,
                requester_email=access_request.requester_email,
                organization_name=access_request.organization_name,
                organization_description=access_request.organization_description,
                slug_preview=access_request.slug_preview,
                status=access_request.status.value,
                created_at=access_request.created_at,
                updated_at=access_request.updated_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)

    async def get_by_id(self, access_request_id: uuid.UUID) -> Optional[AccessRequest]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AccessRequestModel).where(AccessRequestModel.id == access_request_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            return self._model_to_entity(row)

    async def get_by_email(self, email: str) -> Optional[AccessRequest]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AccessRequestModel).where(AccessRequestModel.requester_email == email)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            return self._model_to_entity(row)

    async def list_by_status(
        self,
        status: AccessRequestStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AccessRequest]:
        async with AsyncSessionLocal() as session:
            query = (
                select(AccessRequestModel)
                .where(AccessRequestModel.status == status.value)
                .order_by(AccessRequestModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(query)
            rows = result.scalars().all()
            return [self._model_to_entity(row) for row in rows]

    async def update(self, access_request: AccessRequest) -> AccessRequest:
        async with AsyncSessionLocal() as session:
            model = await session.get(AccessRequestModel, access_request.id)
            if not model:
                raise ValueError("Access request not found")
            model.status = access_request.status.value
            model.rejection_reason = access_request.rejection_reason
            model.reviewed_by = access_request.reviewed_by
            model.reviewed_at = access_request.reviewed_at
            model.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)
