from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, LargeBinary, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from infrastructure.secondary.database.models.base import Base
from domain.enums import ConnectorStatus


class ConnectorInstanceModel(Base):
    __tablename__ = "connector_instance"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    connector_type = Column(String(50), nullable=False)
    connector_implementation = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    config_encrypted = Column(LargeBinary, nullable=True)
    status = Column(SAEnum(ConnectorStatus, name='connector_status', create_type=False, values_callable=lambda enums: [e.value for e in enums]), nullable=False, default=ConnectorStatus.INACTIVO)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)