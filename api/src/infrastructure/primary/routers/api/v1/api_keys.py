from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.output.i_api_key_repository import IAPIKeyRepository
from application.use_cases.others.manage_api_keys import ManageApiKeysUseCase
from core.dependencies import get_current_user, CurrentUser, get_api_key_repository, require_org_access

router = APIRouter(tags=["API Keys"])


class CreateAPIKeyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(None, ge=1)


class APIKeyResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    key: Optional[str] = None
    prefix: str
    is_active: bool
    expires_at: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None


@router.post("/api/v1/organizations/{org_id}/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    org_id: UUID,
    payload: CreateAPIKeyRequest,
    current_user: CurrentUser = Depends(require_org_access()),
    api_key_repo: IAPIKeyRepository = Depends(get_api_key_repository),
):
    try:
        use_case = ManageApiKeysUseCase(api_key_repository=api_key_repo)
        result = await use_case.create_api_key(
            organization_id=org_id,
            name=payload.name,
            expires_in_days=payload.expires_in_days,
        )
        return APIKeyResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/v1/organizations/{org_id}/api-keys")
async def list_api_keys(
    org_id: UUID,
    current_user: CurrentUser = Depends(require_org_access()),
    api_key_repo: IAPIKeyRepository = Depends(get_api_key_repository),
):
    try:
        use_case = ManageApiKeysUseCase(api_key_repository=api_key_repo)
        keys = await use_case.list_api_keys(org_id)
        return keys
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    api_key_repo: IAPIKeyRepository = Depends(get_api_key_repository),
):
    try:
        use_case = ManageApiKeysUseCase(api_key_repository=api_key_repo)
        await use_case.revoke_api_key(key_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))