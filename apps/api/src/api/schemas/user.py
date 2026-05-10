import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from domain.entities.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.OPERATOR


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    organization_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
