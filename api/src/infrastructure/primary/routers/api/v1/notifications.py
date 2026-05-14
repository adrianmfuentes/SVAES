from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated
from application.ports.input.i_notification_service import INotificationService
from core.dependencies import get_current_user, CurrentUser, require_permission, require_role, get_notification_service
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError

router = APIRouter(tags=["Notifications"])


class NotificationChannelConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    channel_type: str = Field(..., description="EMAIL, SLACK, MS_TEAMS")
    enabled: bool = True
    config_data: dict = Field(default_factory=dict, description="Channel-specific configuration")


class UserNotificationPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    release_validated: bool = True
    release_invalidated: bool = True
    release_pending_reminder: bool = False
    weekly_digest: bool = True


class SubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_type: str = Field(..., description="RELEASE_VALIDATED, RELEASE_INVALIDATED, RELEASE_PENDING, WEEKLY_DIGEST")
    enabled: bool = True


@router.get("/api/v1/notifications/channels")
async def list_notification_channels(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Lista los canales de notificación disponibles y su configuración.

    Atributos:
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - Lista de canales de notificación configurados para la organización.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        if current_user.organization_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere organizacion")
        channels = await service.list_channels(organization_id=current_user.organization_id)
        return channels
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/notifications/channels", status_code=status.HTTP_201_CREATED)
async def configure_notification_channel(
    payload: NotificationChannelConfig,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Configura un nuevo canal de notificación para la organización.

    Atributos:
        - payload: Configuración del canal (tipo, habilitado, datos específicos).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - 201 Created con el ID del canal configurado.
        - 403 Forbidden si el usuario no tiene permisos.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        if current_user.organization_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere organizacion")
        channel = await service.configure_channel(
            organization_id=current_user.organization_id,
            channel_type=payload.channel_type,
            enabled=payload.enabled,
            config_data=payload.config_data,
        )
        return {"id": str(channel.id), "type": channel.channel_type, "enabled": channel.enabled}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/notifications/channels/{channel_id}")
async def update_notification_channel(
    channel_id: UUID,
    payload: NotificationChannelConfig,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Actualiza la configuración de un canal de notificación.

    Atributos:
        - channel_id: UUID - El ID del canal a actualizar.
        - payload: Nueva configuración del canal.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - 200 OK con el canal actualizado.
        - 404 Not Found si el canal no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        channel = await service.update_channel(
            channel_id=channel_id,
            enabled=payload.enabled,
            config_data=payload.config_data,
        )
        return channel
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/notifications/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_channel(
    channel_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Elimina un canal de notificación.

    Atributos:
        - channel_id: UUID - El ID del canal a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - 204 No Content si el canal fue eliminado correctamente.
        - 404 Not Found si el canal no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        await service.delete_channel(channel_id=channel_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/v1/notifications/preferences")
async def get_notification_preferences(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Obtiene las preferencias de notificación del usuario actual.

    Atributos:
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - Preferencias de notificación del usuario.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        preferences = await service.get_user_preferences(user_id=current_user.user_id)
        return preferences
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/notifications/preferences")
async def update_notification_preferences(
    payload: UserNotificationPreferences,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Actualiza las preferencias de notificación del usuario actual.

    Atributos:
        - payload: Nuevas preferencias de notificación.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - 200 OK con las preferencias actualizadas.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        preferences = await service.update_user_preferences(
            user_id=current_user.user_id,
            release_validated=payload.release_validated,
            release_invalidated=payload.release_invalidated,
            release_pending_reminder=payload.release_pending_reminder,
            weekly_digest=payload.weekly_digest,
        )
        return preferences
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/notifications/subscriptions", status_code=status.HTTP_201_CREATED)
async def subscribe_to_event(
    payload: SubscriptionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Suscribe al usuario a un tipo de evento de notificación.

    Atributos:
        - payload: Tipo de evento y habilitación.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - 201 Created con la suscripción creada.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        subscription = await service.subscribe(
            user_id=current_user.user_id,
            event_type=payload.event_type,
            enabled=payload.enabled,
        )
        return subscription
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/notifications/subscriptions/{event_type}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_event(
    event_type: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[INotificationService, Depends(get_notification_service)],
):
    """Cancela la suscripción del usuario a un tipo de evento.

    Atributos:
        - event_type: str - El tipo de evento al que desea desuscribirse.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de notificaciones inyectado mediante dependencias.

    Retorna:
        - 204 No Content si la suscripción fue cancelada.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        await service.unsubscribe(user_id=current_user.user_id, event_type=event_type)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))