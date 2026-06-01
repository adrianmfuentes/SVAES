from uuid import UUID, uuid4
from typing import Annotated, Optional
from datetime import datetime, timezone, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field

_log = logging.getLogger(__name__)
from application.ports.output.i_access_request_repository import IAccessRequestRepository
from domain.enums import AccessRequestStatus, UserRole
from domain.entities.access_request import AccessRequest
from domain.entities.user import User
from core.dependencies import get_current_user, CurrentUser, require_role, get_organization_service, get_user_service
from application.ports.input.i_organization_service import IOrganizationService
from application.ports.input.i_user_service import IUserService
from core.email import email_service
from . import ERROR_INTERNO

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


def _get_access_request_repository() -> IAccessRequestRepository:
    from infrastructure.secondary.database.repositories.access_request_repository import (
        SqlAccessRequestRepository,
    )
    return SqlAccessRequestRepository()


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
    repo: Annotated[IAccessRequestRepository, Depends(_get_access_request_repository)],
    user_service: Annotated[IUserService, Depends(get_user_service)],
    org_service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    try:
        existing_request = await repo.get_by_email(payload.requester_email)
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account or pending request already exists for this email.",
            )

        from infrastructure.secondary.database.repositories.user_repository import SqlUserRepository
        user_repo = SqlUserRepository()
        existing_user = await user_repo.get_by_email(payload.requester_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account or pending request already exists for this email.",
            )

        slug = (
            payload.organization_name.lower()
            .strip()
            .replace(" ", "-")
            .replace("--", "-")
            .strip("-")
        )

        now = datetime.now(timezone.utc)
        activation_token = str(uuid4())

        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        hasher = BcryptPasswordHasher()
        temp_password = hasher.hash_password(str(uuid4()))

        user = User(
            id=uuid4(),
            email=payload.requester_email,
            display_name=payload.requester_name,
            hashed_password=temp_password,
            role=UserRole.U4,
            is_active=False,
            activation_token=activation_token,
            activation_token_expiry=now + timedelta(hours=24),
            created_at=now,
            updated_at=now,
        )
        created_user = await user_repo.create(user)

        org = await org_service.create_organization(
            name=payload.organization_name,
            slug=slug,
            owner_id=created_user.id,
        )

        ar = AccessRequest(
            requester_name=payload.requester_name,
            requester_email=payload.requester_email,
            organization_name=payload.organization_name,
            organization_description=payload.organization_description,
            slug_preview=slug,
            status=AccessRequestStatus.APPROVED,
            reviewed_at=now,
            created_at=now,
            updated_at=now,
        )
        created_ar = await repo.create(ar)

        try:
            await email_service.send_activation_email(
                to_email=created_user.email,
                to_name=created_user.display_name,
                token=activation_token,
            )
        except Exception:
            _log.warning(
                "Activation email failed for user %s (org: %s)",
                created_user.email,
                payload.organization_name,
            )

        return {"id": str(created_ar.id), "status": created_ar.status.value}
    except HTTPException:
        raise
    except Exception:
        _log.exception("Unhandled error in create_access_request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_INTERNO,
        )


@router.get("/api/v1/access-requests")
async def list_access_requests(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    repo: Annotated[IAccessRequestRepository, Depends(_get_access_request_repository)],
    status_param: str = Query("PENDING", alias="status"),
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_INTERNO,
        )


@router.patch("/api/v1/access-requests/{access_request_id}")
async def patch_access_request(
    access_request_id: UUID,
    payload: PatchAccessRequestPayload,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    repo: Annotated[IAccessRequestRepository, Depends(_get_access_request_repository)],
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
