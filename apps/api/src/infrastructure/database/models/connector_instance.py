import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.organization import OrganizationModel

class ConnectorInstanceModel(Base):
    __tablename__ = "connector_instance"
    __table_args__ = (Index("ix_connector_org_status", "organization_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    connector_type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    config_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("ACTIVO", "INACTIVO", name="connector_status"),
        default="INACTIVO",
        nullable=False,
    )
    last_tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    organization: Mapped["OrganizationModel"] = relationship(back_populates="connectors")