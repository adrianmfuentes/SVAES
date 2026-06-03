from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from infrastructure.secondary.database.models.base import Base
import enum


class PermissionType(str, enum.Enum):
    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    VIEW_OWN_PROJECTS = "VIEW_OWN_PROJECTS"
    CREATE_RELEASE = "CREATE_RELEASE"
    UPDATE_OWN_RELEASES = "UPDATE_OWN_RELEASES"
    ARCHIVE_RELEASE = "ARCHIVE_RELEASE"
    EXECUTE_VERIFICATION = "EXECUTE_VERIFICATION"
    VIEW_OWN_HISTORY = "VIEW_OWN_HISTORY"
    MANAGE_OWN_API_KEYS = "MANAGE_OWN_API_KEYS"
    VIEW_ORG_PROJECTS = "VIEW_ORG_PROJECTS"
    CREATE_PROJECT = "CREATE_PROJECT"
    UPDATE_PROJECT = "UPDATE_PROJECT"
    DELETE_PROJECT = "DELETE_PROJECT"
    MANAGE_CONNECTORS = "MANAGE_CONNECTORS"
    MANAGE_PROFILES = "MANAGE_PROFILES"
    MANAGE_RULES = "MANAGE_RULES"
    VIEW_ORG_DASHBOARD = "VIEW_ORG_DASHBOARD"
    INVITE_USERS = "INVITE_USERS"
    MANAGE_ROLES = "MANAGE_ROLES"
    TRANSFER_OWNERSHIP = "TRANSFER_OWNERSHIP"
    MANAGE_ORGANIZATIONS = "MANAGE_ORGANIZATIONS"
    MANAGE_ALL_USERS = "MANAGE_ALL_USERS"


class CustomRoleModel(Base):
    __tablename__ = "custom_role"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    name = Column(String(100), nullable=False)
    permissions = Column(ARRAY(String), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))