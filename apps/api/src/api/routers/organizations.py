from typing import Annotated
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from application.use_cases.organization_use_cases import CreateOrganizationUseCase, CreateOrganizationCommand, ListOrganizationsUseCase


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"


router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_org(
    request: OrganizationCreate,
    use_case: Annotated[CreateOrganizationUseCase, Depends()],
):
    command = CreateOrganizationCommand(name=request.name, slug=request.slug, plan=request.plan)
    return await use_case.execute(command)


@router.get("")
async def list_orgs(use_case: Annotated[ListOrganizationsUseCase, Depends()]):
    return await use_case.execute()
