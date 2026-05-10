import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from application.use_cases.organization_use_cases import (
    CreateOrganizationUseCase,
    CreateOrganizationCommand,
    GetOrganizationUseCase,
    ListOrganizationsUseCase,
    UpdateOrganizationUseCase,
    UpdateOrganizationCommand,
    DeleteOrganizationUseCase,
)
from api.dependencies import (
    get_create_organization_use_case,
    get_get_organization_use_case,
    get_list_organizations_use_case,
    get_update_organization_use_case,
    get_delete_organization_use_case,
    get_current_user,
    require_min_role,
)
from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.exceptions import EntityNotFoundError

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrganizationResponse)
async def create_org(
    request: OrganizationCreate,
    use_case: Annotated[CreateOrganizationUseCase, Depends(get_create_organization_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    command = CreateOrganizationCommand(name=request.name, slug=request.slug, plan=request.plan)
    return await use_case.execute(command)


@router.get("", response_model=list[OrganizationResponse])
async def list_orgs(
    use_case: Annotated[ListOrganizationsUseCase, Depends(get_list_organizations_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
):
    return await use_case.execute(skip=skip, limit=limit)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_org(
    organization_id: uuid.UUID,
    use_case: Annotated[GetOrganizationUseCase, Depends(get_get_organization_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await use_case.execute(organization_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_org(
    organization_id: uuid.UUID,
    request: OrganizationUpdate,
    use_case: Annotated[UpdateOrganizationUseCase, Depends(get_update_organization_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        command = UpdateOrganizationCommand(
            organization_id=organization_id,
            name=request.name,
            slug=request.slug,
            is_active=request.is_active,
        )
        return await use_case.execute(command)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    organization_id: uuid.UUID,
    use_case: Annotated[DeleteOrganizationUseCase, Depends(get_delete_organization_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        await use_case.execute(organization_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
