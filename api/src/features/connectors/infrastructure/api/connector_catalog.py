from typing import Annotated
from fastapi import APIRouter, Depends
from bootstrap.dependencies import get_connector_registry, get_current_user, CurrentUser
from features.connectors.application.ports.i_connector_registry import IConnectorRegistry


router = APIRouter(tags=["Connectors"])


_LABEL_EMAIL_ATLASSIAN = "connector_field.atlassian_email"


_LABEL_API_TOKEN = "connector_field.api_token"


_LABEL_BASE_URL = "connector_field.base_url"


_LABEL_API_KEY = "connector_field.api_key"


_LABEL_PERSONAL_ACCESS_TOKEN = "connector_field.personal_access_token"


_LABEL_PROJECT_ID = "connector_field.project_id"


_LABEL_REPOSITORY = "connector_field.repository"


_URL_ATLASSIAN_API = "https://api.atlassian.com"

_EXTRA_UI_CATEGORIES: dict[str, list[str]] = {
    "CLICKUP": ["HERRAMIENTA_PLANIFICACION"],
    "PLANE": ["HERRAMIENTA_PLANIFICACION"],
    "TAIGA": ["HERRAMIENTA_PLANIFICACION"],
    "CUSTOM": ["REPO_CODIGO", "SISTEMA_DOCUMENTAL", "HERRAMIENTA_PLANIFICACION", "GESTION_CAMBIOS"],
}


@router.get("/api/v1/connectors/types")
async def list_connector_types(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    registry: Annotated[IConnectorRegistry, Depends(get_connector_registry)],
):
    """Endpoint para listar los tipos de conectores disponibles y sus implementaciones.

    Retorna la lista de todas las implementaciones de conectores registradas,
    agrupadas por tipo de conector, junto con sus metadatos y esquemas de
    configuración.

    Atributos:
        - current_user: Usuario autenticado con permisos del token JWT.

    Retorna:
        - Diccionario con la lista de implementaciones y la agrupación por tipo.
        - 401 Unauthorized si el token es inválido.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    implementations = registry.list_all_implementations()
    result = []
    for impl_name in implementations:
        conn = registry.get_by_implementation(impl_name)
        result.append({
            "implementation": conn.get_connector_implementation(),
            "type": conn.get_connector_type(),
            "metadata": conn.get_metadata(),
            "config_schema": _get_config_schema(conn.get_connector_implementation()),
        })
    by_type = {}
    for r in result:
        # Some implementations are genuinely both a task manager and a planning
        # tool (ClickUp, Plane, Taiga): they must stay registered with their
        # rule-engine `type` (GESTOR_TAREAS) so category-gated rules like RV-03
        # keep applying to them, but they should still be discoverable under
        # "Herramienta de Planificación" when creating a connector.
        categories = [r["type"]] + _EXTRA_UI_CATEGORIES.get(r["implementation"], [])
        for ct in categories:
            by_type.setdefault(ct, []).append({
                "implementation": r["implementation"],
                "metadata": r["metadata"],
                "config_schema": r["config_schema"],
            })
    return {"implementations": result, "by_type": by_type}


def _get_config_schema(implementation: str) -> dict:
    schemas = {
        "JIRA": {
            "email": {"type": "string", "label": _LABEL_EMAIL_ATLASSIAN, "required": True},
            "api_token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "cloud_id": {"type": "string", "label": "connector_field.cloud_id", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": _URL_ATLASSIAN_API},
        },
        "LINEAR": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
        },
        "TRELLO": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
            "token": {"type": "string", "label": "connector_field.token", "required": True, "sensitive": True},
            "board_id": {"type": "string", "label": "connector_field.board_id", "required": False},
        },
        "ASANA": {
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": True, "sensitive": True},
            "workspace": {"type": "string", "label": "connector_field.workspace_gid", "required": False},
            "project_gid": {"type": "string", "label": "connector_field.project_gid", "required": False},
        },
        "GITLAB": {
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": True, "sensitive": True},
            "project_id": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": "https://gitlab.com/api/v4"},
        },
        "GITHUB": {
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": True, "sensitive": True},
            "owner": {"type": "string", "label": "connector_field.owner_org", "required": False},
            "repo": {"type": "string", "label": _LABEL_REPOSITORY, "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": "https://api.github.com"},
        },
        "BITBUCKET": {
            "token": {"type": "string", "label": "connector_field.app_password", "required": True, "sensitive": True},
            "owner": {"type": "string", "label": "connector_field.workspace", "required": False},
            "repo": {"type": "string", "label": _LABEL_REPOSITORY, "required": False},
        },
        "GITEA": {
            "token": {"type": "string", "label": "connector_field.access_token", "required": True, "sensitive": True},
            "owner": {"type": "string", "label": "connector_field.owner_org", "required": False},
            "repo": {"type": "string", "label": _LABEL_REPOSITORY, "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "CONFLUENCE": {
            "email": {"type": "string", "label": _LABEL_EMAIL_ATLASSIAN, "required": True},
            "api_token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": "connector_field.confluence_url", "required": True},
            "space_key": {"type": "string", "label": "connector_field.space_key", "required": False},
        },
        "NOTION": {
            "token": {"type": "string", "label": "connector_field.integration_token", "required": True, "sensitive": True},
            "database_id": {"type": "string", "label": "connector_field.database_id", "required": False},
        },
        "WIKIJS": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "BOOKSTACK": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "CLICKUP": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "team_id": {"type": "string", "label": "connector_field.team_id", "required": True},
            "list_id": {"type": "string", "label": "connector_field.list_id", "required": False},
        },
        "TAIGA": {
            "token": {"type": "string", "label": "connector_field.auth_token", "required": True, "sensitive": True},
            "project_slug": {"type": "string", "label": "connector_field.project_slug", "required": False},
            "project": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
        },
        "PLANE": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
            "instance_url": {"type": "string", "label": "connector_field.instance_url_plane", "required": False, "default": "https://api.plane.so"},
            "workspace": {"type": "string", "label": "connector_field.workspace_slug", "required": True},
            "project": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
        },
        "MIRO": {
            "token": {"type": "string", "label": "connector_field.access_token", "required": True, "sensitive": True},
        },
        "JIRA_SM": {
            "email": {"type": "string", "label": _LABEL_EMAIL_ATLASSIAN, "required": True},
            "api_token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "site_id": {"type": "string", "label": "connector_field.site_id", "required": False},
            "service_desk_id": {"type": "string", "label": "connector_field.service_desk_id", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": _URL_ATLASSIAN_API},
        },
        "GLPI": {
            "user_token": {"type": "string", "label": "connector_field.user_token", "required": True, "sensitive": True},
            "app_token": {"type": "string", "label": "connector_field.app_token", "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "ZAMMAD": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "REDMINE": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
            "project_id": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
        },
        "CUSTOM": {
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
            "auth_type": {
                "type": "select",
                "label": "connector_field.auth_type",
                "required": True,
                "default": "bearer",
                "options": [
                    {"value": "none", "label": "connector_field.auth_type_none"},
                    {"value": "bearer", "label": "connector_field.auth_type_bearer"},
                    {"value": "basic", "label": "connector_field.auth_type_basic"},
                    {"value": "header", "label": "connector_field.auth_type_header"},
                ],
            },
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": False, "sensitive": True},
            "username": {"type": "string", "label": "connector_field.username", "required": False},
            "password": {"type": "string", "label": "connector_field.password", "required": False, "sensitive": True},
            "auth_header_name": {"type": "string", "label": "connector_field.auth_header_name", "required": False},
            "auth_header_value": {"type": "string", "label": "connector_field.auth_header_value", "required": False, "sensitive": True},
            "health_path": {"type": "string", "label": "connector_field.health_path", "required": False},
            "fetch_path_template": {"type": "string", "label": "connector_field.fetch_path_template", "required": True},
            "fetch_result_key": {"type": "string", "label": "connector_field.fetch_result_key", "required": False},
            "list_path": {"type": "string", "label": "connector_field.list_path", "required": True},
            "list_result_key": {"type": "string", "label": "connector_field.list_result_key", "required": False},
        },
    }
    return schemas.get(implementation, {})
