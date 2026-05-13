import uuid
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

from api.src.domain.enums import ConnectorStatus


class ConnectorCreateRequest(BaseModel):
    connector_type: str
    name: str
    config_data: Dict[str, Any]


class ConnectorUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[Literal["ACTIVO", "INACTIVO"]] = None


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    connector_type: str
    name: str
    status: ConnectorStatus
    last_tested_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VerificationResultResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    verdict: str
    rule_results: dict
    profile_snapshot: dict
    executed_at: datetime
    duration_ms: Optional[int] = None

    model_config = {"from_attributes": True}
