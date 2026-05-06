from pydantic import BaseModel
import uuid
from typing import Dict, Any
from datetime import datetime
from domain.entities.enums import ConnectorStatus

class ConnectorCreateRequest(BaseModel):
    connector_type: str
    name: str
    config_data: Dict[str, Any]

class ConnectorResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    connector_type: str
    name: str
    status: ConnectorStatus
    last_tested_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
