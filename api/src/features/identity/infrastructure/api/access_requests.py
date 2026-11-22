from uuid import UUID
from typing import Annotated, Optional
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field

_log = logging.getLogger(__name__)
from features.identity.application.ports.i_access_request_repository import IAccessRequestRepository
from shared.domain.enums import AccessRequestStatus, UserRole
from features.identity.domain.access_request import AccessRequest
from features.identity.application.use_cases.create_access_request import AccessRequestAlreadyExists, CreateAccessRequest
from features.identity.container import get_access_request_repository
from bootstrap.dependencies import get_current_user, CurrentUser, require_role, get_create_access_request
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors

router = APIRouter(tags=["Access Requests"])


class CreateAccessRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requester_name: str = Field(..., min_length=1, max_length=100)
    requester_email: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=1, max_length=100)
    organization_description: Optional[str] = Field(default=None, max_length=500)


class PatchAccessRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str
    rejection_reason: Optional[str] = Field(default=None, max_length=500)


def _to_response(ar: AccessRequest) -> dict:
    return {
        "id": str(ar.id),
        "requester_name": ar.requester_name,
        "requester_email": ar.requester_email,
        "organization_name": ar.organization_name,
        "organization_description": ar.organization_description,
        "slug_preview": ar.slug_preview,
        "status": ar.status.value,
        "rejection_reason": ar.rejection_reason,
        "created_at": ar.created_at.isoformat() if ar.created_at else None,
    }


@router.post("/api/v1/access-requests", status_code=status.HTTP_201_CREATED)
async def create_access_request(
    payload: CreateAccessRequestPayload,
    use_case: Annotated[CreateAccessRequest, Depends(get_create_access_request)],
):
    try:
        created = await use_case.execute(
            payload.requester_name, payload.requester_email,
            payload.organization_name, payload.organization_description,
        )
        return {"id": str(created.id), "status": created.status.value}
    except AccessRequestAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception:
        _log.exception("Unhandled error in create_access_request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_INTERNO,
        )


@router.get("/api/v1/access-requests")
@handle_internal_errors
async def list_access_requests(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    repo: Annotated[IAccessRequestRepository, Depends(get_access_request_repository)],
    status_param: Annotated[str, Query(alias="status")] = "PENDING",
):
    try:
        ar_status = AccessRequestStatus(status_param)
        results = await repo.list_by_status(status=ar_status)
        return [_to_response(r) for r in results]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_param}",
        )


@router.patch("/api/v1/access-requests/{access_request_id}")
async def patch_access_request(
    access_request_id: UUID,
    payload: PatchAccessRequestPayload,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    repo: Annotated[IAccessRequestRepository, Depends(get_access_request_repository)],
):
    try:
        ar = await repo.get_by_id(access_request_id)
        if not ar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access request not found",
            )

        action = payload.action.upper()
        now = datetime.now(timezone.utc)

        if action == "APPROVE":
            ar.status = AccessRequestStatus.APPROVED
            ar.reviewed_by = current_user.user_id
            ar.reviewed_at = now
        elif action == "REJECT":
            ar.status = AccessRequestStatus.REJECTED
            ar.rejection_reason = payload.rejection_reason
            ar.reviewed_by = current_user.user_id
            ar.reviewed_at = now
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}. Must be APPROVE or REJECT.",
            )

        updated = await repo.update(ar)
        return _to_response(updated)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_INTERNO,
        )
