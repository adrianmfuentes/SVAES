from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from features.organizations.application.ports.i_organization_service import IOrganizationService
from bootstrap.dependencies import (
    get_organization_service,
    CurrentUser,
    require_permission,
    require_org_access,
    require_role,
)
from shared.domain.enums import UserRole, Permission
from shared.domain.exceptions import ValidationError, EntityNotFoundError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors


router = APIRouter(tags=["Organizations"])


class TransferOwnershipRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    new_owner_id: UUID


@router.post("/api/v1/organizations/{org_id}/restore", status_code=status.HTTP_200_OK)
@handle_internal_errors
async def restore_organization(
    org_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Endpoint para restaurar (desarchivar) una organización marcada como inactiva.

    Atributos:
        - org_id: UUID - El ID de la organización a restaurar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID y nombre de la organización restaurada.
        - Lanza HTTPException con status 403 si el usuario no tiene rol U3.
        - Lanza HTTPException con status 404 si la organización no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        org = await service.restore_organization(organization_id=org_id)
        return {"id": str(org.id), "name": org.name, "is_active": org.is_active}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/transfer-ownership", status_code=status.HTTP_200_OK)
async def transfer_ownership(
    org_id: UUID,
    payload: TransferOwnershipRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.TRANSFER_OWNERSHIP))],
    _: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Endpoint para transferir la propiedad de una organización a otro usuario.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: TransferOwnershipRequest - El cuerpo de la solicitud con el ID del nuevo propietario.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la organización actualizada.
        - Lanza HTTPException con status 403 si el usuario no es el propietario actual.
        - Lanza HTTPException con status 404 si la organización no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        existing_org = await service.get_organization(org_id)
        if not existing_org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organización no encontrada: {org_id}")
        if current_user.role != UserRole.U3 and existing_org.owner_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario actual puede transferir la organización")
        org = await service.transfer_ownership(
            organization_id=org_id,
            new_owner_id=payload.new_owner_id,
            requested_by=current_user.user_id,
        )
        return {"id": str(org.id), "name": org.name, "owner_id": str(org.owner_id) if org.owner_id else None}
    except HTTPException:
        raise
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
