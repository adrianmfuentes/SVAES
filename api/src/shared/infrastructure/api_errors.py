from collections.abc import Awaitable, Callable
from functools import wraps

from fastapi import HTTPException


ERROR_INTERNO = "Error interno"
ERROR_PROYECTO_NO_ORGANIZACION = "El proyecto no pertenece a esta organización"
ERROR_PLANTILLA_NO_ENCONTRADA = "Plantilla no encontrada"
ERROR_SIN_ACCESO_PLANTILLA = "No tienes acceso a esta plantilla"


class InternalApiError(Exception):
    pass


def handle_internal_errors[**P, T](endpoint: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    @wraps(endpoint)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await endpoint(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as exc:
            raise InternalApiError from exc

    return wrapped
