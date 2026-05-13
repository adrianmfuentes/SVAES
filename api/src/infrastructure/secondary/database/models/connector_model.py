from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from domain.enums import ConnectorStatus

Base = declarative_base()


class ConnectorInstanceModel(Base):
    __tablename__ = "connector_instance"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    connector_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    encrypted_credentials = Column(LargeBinary, nullable=False)
    status = Column(String(20), nullable=False, default=ConnectorStatus.INACTIVO.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)