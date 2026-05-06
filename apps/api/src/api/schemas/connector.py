from pydantic import BaseModel
import uuid
from typing import Dict, Any
from datetime import datetime
from domain.entities.enums import ConnectorStatus

class ConnectorCreateRequest(BaseModel):
    """Request body for registering a new connector instance in an organization."""
    connector_type: str
    name: str
    config_data: Dict[str, Any]

class ConnectorResponse(BaseModel):
    """API response shape for a persisted connector instance."""
    id: uuid.UUID
    organization_id: uuid.UUID
    connector_type: str
    name: str
    status: ConnectorStatus
    last_tested_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
