"""
Este archivo define los routers para la API.
Aquí se importan los routers de las diferentes versiones de la API y se exportan para su uso en la aplicación principal.
"""
from infrastructure.primary.routers.api.v1.releases import router as releases_router
from infrastructure.primary.routers.api.v1.auth import router as auth_router
from infrastructure.primary.routers.api.v1.organizations import router as organizations_router
from infrastructure.primary.routers.api.v1.connectors import router as connectors_router
from infrastructure.primary.routers.api.v1.profiles import router as profiles_router
from infrastructure.primary.routers.api.v1.tasks import router as tasks_router
from infrastructure.primary.routers.api.v1.users import router as users_router
from infrastructure.primary.routers.api.v1.custom_roles import router as custom_roles_router
from infrastructure.primary.routers.api.v1.dashboard import router as dashboard_router
from infrastructure.primary.routers.api.v1.api_keys import router as api_keys_router

__all__ = [
    "auth_router",
    "organizations_router",
    "releases_router",
    "connectors_router",
    "profiles_router",
    "tasks_router",
    "users_router",
    "custom_roles_router",
    "dashboard_router",
    "api_keys_router",
]