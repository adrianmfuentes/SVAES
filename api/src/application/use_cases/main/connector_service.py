import ast
import re
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from application.ports.input.i_connector_service import IConnectorService
from application.ports.output.i_connector_repository import IConnectorRepository
from application.ports.output.i_connector_registry import IConnectorRegistry
from core.config import settings
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus, ConnectorType
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError

_log = get_logger(__name__)

_CREDENTIAL_QUERY_PARAMS = {"key", "token", "api_key", "apikey", "access_token", "secret"}

GENERIC_CONNECTOR_IMPLEMENTATION = "CUSTOM"


def _redact_exc(exc: Exception) -> str:
    """Representación de una excepción segura para loguear.

    `httpx.HTTPStatusError`/`ConnectError` incluyen la URL completa de la
    petición fallida en su `str()`. Algunos conectores (p. ej. Trello)
    autentican vía query string, por lo que esa URL puede llevar la API
    key/token en claro - se redacta antes de loguear.
    """
    request = getattr(exc, "request", None)
    url = getattr(request, "url", None) if request is not None else None
    if url is None:
        response = getattr(exc, "response", None)
        url = getattr(getattr(response, "request", None), "url", None) if response is not None else None
    if url is not None:
        try:
            redacted_query = "&".join(
                f"{k}=***" if k.lower() in _CREDENTIAL_QUERY_PARAMS else f"{k}={v}"
                for k, v in url.params.multi_items()
            )
            safe_url = str(url.copy_with(query=redacted_query.encode() if redacted_query else None))
            return f"{type(exc).__name__}: {safe_url}"
        except Exception:
            return f"{type(exc).__name__} (url redacted)"
    return str(exc)


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
        is_generic = connector_implementation.upper() == GENERIC_CONNECTOR_IMPLEMENTATION
        existing = await self._connector_repo.list_by_organization(organization_id, active_only=False, skip=0, limit=1000)
        for c in existing:
            if c.connector_implementation == connector_implementation and not is_generic:
                raise DuplicateEntityError(f"Ya existe un conector {connector_implementation} en esta organización")

        if is_generic and connector_type not in {t.value for t in ConnectorType}:
            raise ValidationError(f"Tipo de conector '{connector_type}' no soportado")

        from cryptography.fernet import Fernet

        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
        encrypted_credentials = fernet.encrypt(str(config).encode())

        initial_status = ConnectorStatus.ERROR
        connector_impl = self._get_connector_impl(connector_implementation)
        if connector_impl:
            if not is_generic:
                connector_type = connector_impl.get_connector_type()
            try:
                initial_status = ConnectorStatus.ACTIVO if await connector_impl.test_connection(config) else ConnectorStatus.ERROR
            except Exception:
                initial_status = ConnectorStatus.ERROR

        connector = ConnectorInstance(
            id=uuid4(),
            organization_id=organization_id,
            connector_type=connector_type,
            connector_implementation=connector_implementation,
            name=name,
            encrypted_credentials=encrypted_credentials,
            status=initial_status,
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

        connector_impl = self._get_connector_impl(connector.connector_implementation)
        if not connector_impl:
            raise ValidationError(f"Implementación '{connector.connector_implementation}' no soportada")

        from cryptography.fernet import Fernet
        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]

        connection_ok = False
        try:
            decrypted_config = ast.literal_eval(fernet.decrypt(connector.encrypted_credentials).decode())
            connection_ok = await connector_impl.test_connection(decrypted_config)
        except Exception as exc:
            _log.error("Connector test failed: id=%s org=%s error=%s", connector_id, connector.organization_id, _redact_exc(exc))

        connector.last_tested_at = datetime.now(timezone.utc)
        connector.status = ConnectorStatus.ACTIVO if connection_ok else ConnectorStatus.ERROR
        updated = await self._connector_repo.update(connector)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_TESTED,
            user_id=requested_by,
            organization_id=connector.organization_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"success": connection_ok, "implementation": connector.connector_implementation},
        ))
        _log.info("Connector tested: id=%s org=%s result=%s", connector_id, connector.organization_id, connection_ok)

        if not connection_ok:
            raise ConnectorConnectionFailedError(f"Error al probar conexión del conector: {connector_id}")

        return updated


    def _get_connector_impl(self, connector_implementation: str):
        try:
            return self._connector_registry.get_by_implementation(connector_implementation)
        except KeyError:
            raise ValidationError(f"Implementación '{connector_implementation}' no soportada")


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
        from domain.exceptions import ConnectorConnectionFailedError
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
            config = ast.literal_eval(fernet.decrypt(connector.encrypted_credentials).decode())
        except Exception as exc:
            _log.error("browse: credential decrypt failed connector_id=%s: %s", connector_id, exc)
            raise ConnectorConnectionFailedError(
                f"No se pudieron descifrar las credenciales del conector: {connector_id}"
            ) from exc

        filter_params: dict = {}
        if query:
            impl_upper = connector.connector_implementation.upper()
            escaped = query.replace('"', '\\"')
            if impl_upper in ("JIRA", "JIRA_SM"):
                key_clause = ""
                if re.match(r"^[A-Za-z][A-Za-z0-9_]+-\d+$", query.strip()):
                    key_clause = f'key = "{query.strip().upper()}" OR '
                filter_params["jql"] = (
                    f'{key_clause}text ~ "{escaped}" OR fixVersion = "{escaped}" ORDER BY updated DESC'
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
                "browse: list_artifacts failed connector_id=%s: %s",
                connector_id, _redact_exc(exc),
            )
            raise ConnectorConnectionFailedError(
                f"Error al listar elementos del conector: {connector_id}"
            ) from exc

        try:
            return _normalize_browse_items(raw_items, connector.connector_implementation, config)
        except Exception as exc:
            _log.warning(
                "browse: normalization failed connector_id=%s: %s",
                connector_id, exc,
            )
            raise ConnectorConnectionFailedError(
                f"Error al normalizar elementos del conector: {connector_id}"
            ) from exc


    async def verify_artifact_ref(
        self, connector_id: UUID, external_ref: str, organization_id: Optional[UUID] = None
    ) -> None:
        import httpx
        from cryptography.fernet import Fernet
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")

        if organization_id is not None and connector.organization_id != organization_id:
            raise ValidationError(f"Conector {connector_id} no pertenece a la organización de esta release")

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
            config = ast.literal_eval(fernet.decrypt(connector.encrypted_credentials).decode())
        except Exception as exc:
            _log.error("verify_ref: credential decrypt failed connector_id=%s: %s", connector_id, exc)
            return

        try:
            await connector_impl.fetch_artifact(external_ref, config)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404 and connector.status == ConnectorStatus.ACTIVO:
                raise ValidationError(
                    f"La referencia externa '{external_ref}' no existe en el conector '{connector.connector_implementation}'. "
                    f"Verifique que el identificador es correcto y que las credenciales tienen acceso."
                )
            _log.warning(
                "verify_ref: non-404 HTTP error for connector_id=%s: %s",
                connector_id, _redact_exc(exc),
            )
        except Exception as exc:
            _log.warning(
                "verify_ref: could not verify for connector_id=%s (connectivity issue): %s",
                connector_id, _redact_exc(exc),
            )

    async def configure_webhook(
        self,
        connector_id: UUID,
        enabled: bool,
        requested_by: UUID,
        regenerate_secret: bool = False,
    ) -> Tuple[ConnectorInstance, Optional[str]]:
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        if connector.connector_type != "REPO_CODIGO":
            raise ValidationError(
                "Los webhooks entrantes solo están disponibles para conectores de tipo REPO_CODIGO."
            )

        plaintext_secret: Optional[str] = None
        if enabled and (regenerate_secret or not connector.webhook_secret_encrypted):
            from cryptography.fernet import Fernet

            plaintext_secret = secrets.token_urlsafe(32)
            fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
            connector.webhook_secret_encrypted = fernet.encrypt(plaintext_secret.encode())

        connector.webhook_enabled = enabled
        updated = await self._connector_repo.update(connector)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.CONNECTOR_UPDATED,
            user_id=requested_by,
            organization_id=connector.organization_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"webhook_enabled": enabled},
        ))
        _log.info("Connector webhook configured: id=%s enabled=%s", connector_id, enabled)

        return updated, plaintext_secret


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