"""
Este archivo define las dependencias que se pueden inyectar en los endpoints de FastAPI.
Estas dependencias pueden ser utilizadas para manejar la autenticación, autorización, validación de datos, entre otras funcionalidades comunes en los endpoints.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
from infrastructure.secondary.database.repositories.project_repository import SqlProjectRepository
from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.primary.middleware.jwt_handler import JwtHandler
from core.config import Settings, get_settings
from application.use_cases.main.release_service import CreateReleaseUseCase
from application.ports.input.i_release_service import IReleaseService
from application.ports.input.i_artifact_service import IArtifactService
from application.ports.input.i_verification_service import IVerificationService

_bearer = HTTPBearer()

def get_project_repository() -> SqlProjectRepository:
    return SqlProjectRepository()


def get_release_repository() -> SqlReleaseRepository:
    return SqlReleaseRepository()


def get_settings_dependency() -> Settings:
    return get_settings()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> UUID:
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        return payload.user_id
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def get_release_service(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> IReleaseService:
    return CreateReleaseUseCase(
        release_repository=release_repo,
        project_repository=project_repo,
    )


def get_artifact_service() -> IArtifactService:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="No implementado")


def get_verification_service() -> IVerificationService:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="No implementado")

