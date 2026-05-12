import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_VALID_TEMPLATES = {f"RV-{i:02d}" for i in range(1, 11)}
_VALID_SEVERITIES = {"OBLIGATORIA", "RECOMENDADA", "INFORMATIVA"}


class RuleCreateRequest(BaseModel):
    rule_template: str
    severity: str = "OBLIGATORIA"
    params: dict = Field(default_factory=dict)
    connector_instance_id: Optional[uuid.UUID] = None
    display_order: int = 0

    @field_validator("rule_template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        if v not in _VALID_TEMPLATES:
            raise ValueError(f"rule_template must be one of {sorted(_VALID_TEMPLATES)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_VALID_SEVERITIES)}")
        return v


class RuleUpdateRequest(BaseModel):
    rule_template: Optional[str] = None
    severity: Optional[str] = None
    params: Optional[dict] = None
    connector_instance_id: Optional[uuid.UUID] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("rule_template")
    @classmethod
    def validate_template(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_TEMPLATES:
            raise ValueError(f"rule_template must be one of {sorted(_VALID_TEMPLATES)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_VALID_SEVERITIES)}")
        return v


class RuleResponse(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    rule_template: str
    severity: str
    params: dict
    connector_instance_id: Optional[uuid.UUID]
    display_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
