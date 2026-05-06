from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from application.use_cases.organization_use_cases import CreateOrganizationUseCase, CreateOrganizationCommand, ListOrganizationsUseCase
from api.dependencies import get_create_organization_use_case, get_list_organizations_use_case

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_org(
    request: OrganizationCreate,
    use_case: Annotated[CreateOrganizationUseCase, Depends(get_create_organization_use_case)],
):
    command = CreateOrganizationCommand(name=request.name, slug=request.slug, plan=request.plan)
    return await use_case.execute(command)


@router.get("")
async def list_orgs(
    use_case: Annotated[ListOrganizationsUseCase, Depends(get_list_organizations_use_case)],
):
    return await use_case.execute()
