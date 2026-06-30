from uuid import UUID
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from application.ports.input.i_profile_service import IProfileService
from core.dependencies import get_profile_service, get_current_user, CurrentUser, require_permission, require_role, require_org_access, require_profile_access, require_rule_access
from domain.enums import SeverityType, Permission
from domain.exceptions import EntityNotFoundError, ValidationError
from core.rule_names import RULE_CONNECTOR_TYPES, RULE_CONNECTOR_TYPES_MODE
from . import ERROR_INTERNO

router = APIRouter(tags=["Profiles"])

class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    is_default: bool = Field(default=False)

class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: Optional[bool] = None

class RuleCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rule_template: str = Field(..., min_length=1, max_length=100)
    severity: SeverityType = Field(default=SeverityType.HIGH)
    connector_instance_id: Optional[UUID] = None
    params: dict = Field(default_factory=dict)
    display_order: int = Field(default=0)

class RuleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    severity: Optional[SeverityType] = None
    connector_instance_id: Optional[UUID] = None
    params: Optional[dict] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/api/v1/organizations/{org_id}/profiles")
async def list_profiles(
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
):
    """Endpoint para listar los perfiles de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - skip: int - Número de registros a omitir para paginación.
        - limit: int - Número máximo de registros a retornar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias

    Retorna:
        - Una lista de diccionarios con la información de cada perfil, incluyendo el conteo de reglas asociadas.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        profiles = await service.list_profiles(organization_id=org_id, skip=skip, limit=limit)
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "is_default": p.is_default,
                "is_system": p.is_system,
                "rules_count": len(p.rules),
            }
            for p in profiles
        ]
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/organizations/{org_id}/profiles", status_code=status.HTTP_201_CREATED)
async def create_profile(
    org_id: UUID,
    payload: ProfileCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para crear un nuevo perfil dentro de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: ProfileCreateRequest - El cuerpo de la solicitud con los datos del perfil a crear.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información del perfil creado (id, name, is_default).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 409 si hay un error de validación.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        profile = await service.create_profile(
            organization_id=org_id,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )
        return {"id": str(profile.id), "name": profile.name, "is_default": profile.is_default}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.patch("/api/v1/profiles/{profile_id}")
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    _: Annotated[None, Depends(require_profile_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para actualizar un perfil existente.

    Atributos:
        - profile_id: UUID - El ID del perfil a actualizar.
        - payload: ProfileUpdateRequest - El cuerpo de la solicitud con los datos del perfil a actualizar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información del perfil actualizado (id, name, is_default).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el perfil no existe.
        - Lanza HTTPException con status 409 si hay un error de validación.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        profile = await service.update_profile(
            profile_id=profile_id,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )
        return {"id": str(profile.id), "name": profile.name, "is_default": profile.is_default}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.delete("/api/v1/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    _: Annotated[None, Depends(require_profile_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para eliminar un perfil existente.

    Atributos:
        - profile_id: UUID - El ID del perfil a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias.
    Retorna:
        - No retorna contenido (204 No Content) si la eliminación es exitosa.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el perfil no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        await service.delete_profile(profile_id, requested_by=current_user.user_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/profiles/{profile_id}")
async def get_profile(
    profile_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    _: Annotated[None, Depends(require_profile_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para obtener un perfil con sus reglas.

    Atributos:
        - profile_id: UUID - El ID del perfil a obtener.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información del perfil y sus reglas.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el perfil no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        profile = await service.get_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
        return {
            "id": str(profile.id),
            "name": profile.name,
            "description": profile.description,
            "is_default": profile.is_default,
            "is_system": profile.is_system,
            "rules": [
                {
                    "id": str(r.id),
                    "rule_template": r.rule_template,
                    "severity": r.severity.value,
                    "connector_instance_id": str(r.connector_instance_id) if r.connector_instance_id else None,
                    "params": r.params,
                    "display_order": r.display_order,
                    "is_active": r.is_active,
                    "connector_types": RULE_CONNECTOR_TYPES.get(r.rule_template, []),
                    "connector_types_mode": RULE_CONNECTOR_TYPES_MODE.get(r.rule_template, "ALL"),
                }
                for r in profile.rules
            ],
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/profiles/{profile_id}/rules", status_code=status.HTTP_201_CREATED)
async def add_rule(
    profile_id: UUID,
    payload: RuleCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_RULES))],
    _: Annotated[None, Depends(require_profile_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para agregar una nueva regla a un perfil existente.

    Atributos:
        - profile_id: UUID - El ID del perfil al que se agregará la regla.
        - payload: RuleCreateRequest - El cuerpo de la solicitud con los datos de la regla a crear.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la regla creada (id, rule_template).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el perfil no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        rule = await service.add_rule(
            profile_id=profile_id,
            rule_template=payload.rule_template,
            severity=payload.severity,
            connector_instance_id=payload.connector_instance_id,
            params=payload.params,
            display_order=payload.display_order,
        )
        return {"id": str(rule.id), "rule_template": rule.rule_template}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        import logging
        logging.exception("Error adding rule to profile %s: %s", profile_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/rules/{rule_id}")
async def update_rule(
    rule_id: UUID,
    payload: RuleUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_RULES))],
    _: Annotated[None, Depends(require_rule_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para actualizar una regla existente.

    Atributos:
        - rule_id: UUID - El ID de la regla a actualizar.
        - payload: RuleUpdateRequest - El cuerpo de la solicitud con los datos de la regla a actualizar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la regla actualizada (id, is_active).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si la regla no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        rule = await service.update_rule(
            rule_id=rule_id,
            severity=payload.severity,
            connector_instance_id=payload.connector_instance_id,
            params=payload.params,
            display_order=payload.display_order,
            is_active=payload.is_active,
            requested_by=current_user.user_id,
        )
        return {"id": str(rule.id), "is_active": rule.is_active}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.delete("/api/v1/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_RULES))],
    _: Annotated[None, Depends(require_rule_access())],
    service: Annotated[IProfileService, Depends(get_profile_service)],
):
    """Endpoint para eliminar una regla existente.

    Atributos:
        - rule_id: UUID - El ID de la regla a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IProfileService - El servicio de perfiles, inyectado mediante dependencias

    Retorna:
        - No retorna contenido (204 No Content) si la eliminación es exitosa.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si la regla no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        await service.delete_rule(rule_id, requested_by=current_user.user_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)