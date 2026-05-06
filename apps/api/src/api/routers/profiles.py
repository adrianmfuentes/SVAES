import uuid
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from application.use_cases.manage_profile import ManageProfileUseCase, CreateProfileCommand
from api.dependencies import get_manage_profile_use_case


class ProfileCreate(BaseModel):
    organization_id: uuid.UUID
    name: str


router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(
    request: ProfileCreate,
    use_case: ManageProfileUseCase = Depends(get_manage_profile_use_case),
):
    command = CreateProfileCommand(
        organization_id=request.organization_id,
        name=request.name,
    )
    return await use_case.create_profile(command)
