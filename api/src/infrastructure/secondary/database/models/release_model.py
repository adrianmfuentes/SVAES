from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from infrastructure.secondary.database.models.base import Base
from domain.enums import ReleaseStatus

class ReleaseModel(Base):
    __tablename__ = "release"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("verification_profile.id"), nullable=True)
    version = Column(String(50), nullable=False)
    status = Column(SAEnum(ReleaseStatus, name='release_status', create_type=False, values_callable=lambda enums: [e.value for e in enums]), nullable=False, default=ReleaseStatus.BORRADOR)
    description = Column(String(1000), nullable=True, default="")
    name = Column(String(100), nullable=False)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Asegura que no haya dos releases con la misma versión dentro del mismo proyecto
        UniqueConstraint("project_id", "version", name="uq_release_project_version"),
    )