"""
Este archivo define los routers para la API.
Aquí se importan los routers de las diferentes versiones de la API y se exportan para su uso en la aplicación principal.
"""
from features.projects_releases.infrastructure.api.releases import router as releases_router
from features.identity.infrastructure.api.auth import router as auth_router
from features.organizations.infrastructure.api.organizations import router as organizations_router
from features.connectors.infrastructure.api.connectors import router as connectors_router
from features.verification.infrastructure.api.profiles import router as profiles_router
from features.verification.infrastructure.api.tasks import router as tasks_router
from features.identity.infrastructure.api.users import router as users_router
from features.identity.infrastructure.api.custom_roles import router as custom_roles_router
from features.reporting.infrastructure.api.dashboard import router as dashboard_router
from features.identity.infrastructure.api.api_keys import router as api_keys_router
from features.verification.infrastructure.api.templates import router as templates_router
from features.notifications.infrastructure.api.notifications import router as notifications_router
from features.admin.infrastructure.api.admin import router as admin_router
from features.audit.infrastructure.api.audit import router as audit_router
from features.identity.infrastructure.api.access_requests import router as access_requests_router
from features.feedback.infrastructure.api.feedback import router as feedback_router
from features.connectors.infrastructure.api.webhooks import router as webhooks_router

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
    "templates_router",
    "notifications_router",
    "admin_router",
    "audit_router",
    "access_requests_router",
    "feedback_router",
    "webhooks_router",
]