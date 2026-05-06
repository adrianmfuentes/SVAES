import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.verification_profile import VerificationProfileModel


class VerificationRuleModel(Base):
    __tablename__ = "verification_rule"
    __table_args__ = (Index("ix_verification_rule_profile_id", "profile_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("verification_profile.id"), nullable=False)
    connector_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_instance.id"), nullable=True)
    rule_template: Mapped[str] = mapped_column(String, nullable=False)  # RV-01 .. RV-10
    params: Mapped[dict] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(
        Enum("OBLIGATORIA", "RECOMENDADA", "INFORMATIVA", name="severity_type"),
        default="OBLIGATORIA",
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    profile: Mapped["VerificationProfileModel"] = relationship(back_populates="rules")