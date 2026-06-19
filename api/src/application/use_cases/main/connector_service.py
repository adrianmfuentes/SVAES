from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from application.ports.input.i_connector_service import IConnectorService
from application.ports.output.i_connector_repository import IConnectorRepository
from application.ports.output.i_connector_registry import IConnectorRegistry
from core.config import settings
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError

_log = get_logger(__name__)


class ConnectorService(IConnectorService):
    def __init__(
        self,
        connector_repository: IConnectorRepository,
        connector_registry: IConnectorRegistry,
    ) -> None:
        self._connector_repo = connector_repository
        self._connector_registry = connector_registry


    async def register_connector(
        self,
        organization_id: UUID,
        connector_type: str,
        connector_implementation: str,
        name: str,
        config: dict,
        requested_by: UUID,
    ) -> ConnectorInstance:
        existing = await self._connector_repo.list_by_organization(organization_id, active_only=False, skip=0, limit=1000)
        for c in existing:
            if c.connector_implementation == connector_implementation:
                raise DuplicateEntityError(f"Ya existe un conector {connector_implementation} en esta organización")

        from cryptography.fernet import Fernet

        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
        encrypted_credentials = fernet.encrypt(str(config).encode())

        connector = ConnectorInstance(
            id=uuid4(),
            organization_id=organization_id,
            connector_type=connector_type,
            connector_implementation=connector_implementation,
            name=name,
            encrypted_credentials=encrypted_credentials,
            status=ConnectorStatus.ACTIVO,
        )
        saved = await self._connector_repo.save(connector)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_CREATED,
            user_id=requested_by,
            organization_id=organization_id,
            resource_type="connector",
            resource_id=saved.id,
            details={"name": name, "type": connector_type},
        ))
        _log.info("Connector registered: org=%s type_len=%d", organization_id, len(connector_type))

        return saved


    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        requested_by: Optional[UUID] = None,
    ) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        if name:
            connector.name = name
        if config:
            from cryptography.fernet import Fernet
            fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
            connector.encrypted_credentials = fernet.encrypt(str(config).encode())

        updated = await self._connector_repo.update(connector)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_UPDATED,
            user_id=requested_by or uuid4(),
            organization_id=connector.organization_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"name": connector.name} if name else {},
        ))
        _log.info("Connector updated: id=%s org=%s", connector_id, connector.organization_id)

        return updated


    async def test_connector_connection(self, connector_id: UUID, requested_by: UUID) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        from domain.exceptions import ConnectorConnectionFailedError
        from application.ports.output.i_connector import IConnector

        connector_impl = self._get_connector_impl(connector.connector_implementation)
        if not connector_impl:
            raise ValidationError(f"Implementación '{connector.connector_implementation}' no soportada")

        from cryptography.fernet import Fernet
        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]

        try:
            decrypted_config = eval(fernet.decrypt(connector.encrypted_credentials).decode())
            result = await connector_impl.test_connection(decrypted_config)
            connector.last_tested_at = datetime.now(timezone.utc)
            if result:
                connector.status = ConnectorStatus.ACTIVO
            updated = await self._connector_repo.update(connector)

            audit = get_audit_logger()
            audit.log(AuditEntry(
                event=AuditEvent.CONNECTOR_TESTED,
                user_id=requested_by,
                organization_id=connector.organization_id,
                resource_type="connector",
                resource_id=connector_id,
                details={"success": result, "implementation": connector.connector_implementation},
            ))
            _log.info("Connector tested: id=%s org=%s result=%s", connector_id, connector.organization_id, result)

            return updated
        except Exception as exc:
            _log.exception("Connector test failed: id=%s org=%s error=%s", connector_id, connector.organization_id, exc)
            connector.status = ConnectorStatus.ERROR
            connector.last_tested_at = datetime.now(timezone.utc)
            await self._connector_repo.update(connector)
            raise ConnectorConnectionFailedError(f"Error al probar conexión del conector: {connector_id}") from exc


    def _get_connector_impl(self, connector_implementation: str):
        connector_impl = self._connector_registry.get_by_implementation(connector_implementation)
        return connector_impl


    async def list_connectors(
        self,
        organization_id: UUID,
        active_only: bool = True,
    ) -> List[ConnectorInstance]:
        return await self._connector_repo.list_by_organization(
            organization_id, active_only=active_only, skip=0, limit=50
        )


    async def get_connector(self, connector_id: UUID) -> Optional[ConnectorInstance]:
        return await self._connector_repo.get_by_id(connector_id)


    async def delete_connector(self, connector_id: UUID, requested_by: UUID) -> None:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        org_id = connector.organization_id
        await self._connector_repo.delete(connector_id)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_DELETED,
            user_id=requested_by,
            organization_id=org_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"name": connector.name},
        ))
        _log.info("Connector deleted: id=%s org=%s", connector_id, org_id)


    async def toggle_connector_status(
        self, connector_id: UUID, status: ConnectorStatus, requested_by: UUID
    ) -> ConnectorInstance:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        connector.status = status
        return await self._connector_repo.update(connector)


    async def browse_connector_items(
        self, connector_id: UUID, query: str = ""
    ) -> List[dict]:
        from cryptography.fernet import Fernet
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        try:
            connector_impl = self._connector_registry.get_by_implementation(
                connector.connector_implementation
            )
        except KeyError:
            raise ValidationError(
                f"Implementación '{connector.connector_implementation}' no soportada"
            )

        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
        try:
            config = eval(fernet.decrypt(connector.encrypted_credentials).decode())
        except Exception as exc:
            _log.error("browse: credential decrypt failed connector_id=%s: %s", connector_id, exc)
            return []

        filter_params: dict = {}
        if query:
            impl_upper = connector.connector_implementation.upper()
            escaped = query.replace('"', '\\"')
            if impl_upper in ("JIRA", "JIRA_SM"):
                filter_params["jql"] = (
                    f'text ~ "{escaped}" OR fixVersion = "{escaped}" ORDER BY updated DESC'
                )
            elif impl_upper == "CONFLUENCE":
                filter_params["cql"] = f'text ~ "{escaped}" order by lastmodified desc'
            elif impl_upper in ("GITLAB", "GITHUB", "GITEA", "BITBUCKET"):
                filter_params["search"] = query
            elif impl_upper in ("CLICKUP", "PLANE", "TAIGA"):
                filter_params["query_text"] = query
            else:
                filter_params["query"] = query

        try:
            raw_items = await connector_impl.list_artifacts(filter_params, config)
        except Exception as exc:
            _log.warning(
                "browse: list_artifacts failed connector_id=%s impl=%s: %s",
                connector_id, connector.connector_implementation, exc,
            )
            return []

        try:
            return _normalize_browse_items(raw_items, connector.connector_implementation, config)
        except Exception as exc:
            _log.warning(
                "browse: normalization failed connector_id=%s impl=%s: %s",
                connector_id, connector.connector_implementation, exc,
            )
            return []


def _normalize_browse_items(items: list, implementation: str, config: dict) -> list:
    impl = implementation.upper()
    result = []
    for item in items:
        try:
            entry = _map_item(item, impl, config)
            if entry and entry.get("ref"):
                result.append(entry)
        except Exception:
            continue
    return result


_ITEM_MAPPERS = {
    "JIRA": lambda item, config: _map_jira_item(item),
    "JIRA_SM": lambda item, config: _map_jira_item(item),
    "GITHUB": lambda item, config: _map_github_gitea_item(item, config),
    "GITEA": lambda item, config: _map_github_gitea_item(item, config),
    "GITLAB": lambda item, config: _map_gitlab_item(item, config),
    "BITBUCKET": lambda item, config: _map_bitbucket_item(item, config),
    "CONFLUENCE": lambda item, config: {"ref": item.get("id", ""), "title": item.get("title", ""), "subtitle": item.get("type", "")},
    "LINEAR": lambda item, config: _map_linear_item(item),
    "ASANA": lambda item, config: {"ref": item.get("gid", ""), "title": item.get("name", ""), "subtitle": ""},
    "TRELLO": lambda item, config: {"ref": item.get("id", ""), "title": item.get("name", ""), "subtitle": ""},
    "CLICKUP": lambda item, config: _map_status_item(item),
    "PLANE": lambda item, config: _map_status_item(item),
    "TAIGA": lambda item, config: _map_status_item(item),
    "NOTION": lambda item, config: _map_notion_item(item),
    "WIKIJS": lambda item, config: {"ref": str(item.get("id", "")), "title": item.get("title", "") or item.get("name", ""), "subtitle": ""},
    "BOOKSTACK": lambda item, config: {"ref": str(item.get("id", "")), "title": item.get("title", "") or item.get("name", ""), "subtitle": ""},
    "GLPI": lambda item, config: _map_name_status_item(item),
    "ZAMMAD": lambda item, config: _map_name_status_item(item),
    "REDMINE": lambda item, config: _map_name_status_item(item),
}


def _map_jira_item(item: dict) -> dict:
    fields = item.get("fields", {})
    return {
        "ref": item.get("key", ""),
        "title": fields.get("summary", ""),
        "subtitle": (fields.get("status") or {}).get("name", ""),
    }


def _map_github_gitea_item(item: dict, config: dict) -> dict:
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    number = item.get("number", "")
    return {
        "ref": f"{owner}/{repo}/{number}",
        "title": item.get("title", ""),
        "subtitle": item.get("state", ""),
    }


def _map_gitlab_item(item: dict, config: dict) -> dict:
    project_id = config.get("project_id", "")
    return {
        "ref": f"{project_id}/{item.get('iid', '')}",
        "title": item.get("title", ""),
        "subtitle": item.get("state", ""),
    }


def _map_bitbucket_item(item: dict, config: dict) -> dict:
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    pr_id = item.get("id", "")
    return {
        "ref": f"{owner}/{repo}/{pr_id}",
        "title": item.get("title", ""),
        "subtitle": (item.get("state") or "").lower(),
    }


def _map_linear_item(item: dict) -> dict:
    state = item.get("state") or {}
    return {
        "ref": item.get("identifier", ""),
        "title": item.get("title", ""),
        "subtitle": state.get("name", "") if isinstance(state, dict) else "",
    }


def _map_status_item(item: dict) -> dict:
    status = item.get("status", "")
    subtitle = status.get("status", "") if isinstance(status, dict) else str(status)
    return {
        "ref": str(item.get("id", "")),
        "title": item.get("name", "") or item.get("title", ""),
        "subtitle": subtitle,
    }


def _map_notion_item(item: dict) -> dict:
    props = item.get("properties", {})
    title_prop = props.get("Name", props.get("title", {}))
    title_arr = title_prop.get("title", []) if isinstance(title_prop, dict) else []
    title = title_arr[0].get("text", {}).get("content", "") if title_arr else ""
    return {"ref": item.get("id", ""), "title": title, "subtitle": ""}


def _map_name_status_item(item: dict) -> dict:
    return {
        "ref": str(item.get("id", "")),
        "title": item.get("name", "") or item.get("title", "") or item.get("subject", ""),
        "subtitle": str(item.get("status", "")),
    }


def _map_item(item: dict, impl: str, config: dict) -> dict:
    mapper = _ITEM_MAPPERS.get(impl)
    if mapper:
        return mapper(item, config)
    ref = str(item.get("id", "") or item.get("key", "") or item.get("ref", ""))
    title = str(item.get("name", "") or item.get("title", "") or item.get("summary", "") or ref)
    return {"ref": ref, "title": title, "subtitle": ""}