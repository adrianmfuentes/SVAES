from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from infrastructure.secondary.database.models.base import Base
from domain.enums import AccessRequestStatus


class AccessRequestModel(Base):
    __tablename__ = "access_request"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_name = Column(String(100), nullable=False)
    requester_email = Column(String(255), nullable=False, index=True)
    organization_name = Column(String(100), nullable=False)
    organization_description = Column(String(500), nullable=True)
    slug_preview = Column(String(100), nullable=True)
    status = Column(
        Enum(AccessRequestStatus, name="access_request_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AccessRequestStatus.PENDING,
    )
    rejection_reason = Column(String(500), nullable=True)
    reviewed_by = Column(PG_UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
