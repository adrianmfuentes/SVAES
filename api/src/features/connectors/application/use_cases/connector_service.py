import logging
import ast
import re
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from features.connectors.application.browse_items import normalize_browse_items
from features.connectors.application.ports.i_connector_service import IConnectorService
from shared.application.i_credential_encryptor import ICredentialEncryptor
from features.connectors.application.ports.i_connector_repository import IConnectorRepository
from features.connectors.application.ports.i_connector_artifact_probe import IConnectorArtifactProbe
from features.connectors.application.ports.i_connector_registry import IConnectorRegistry
from shared.application.i_audit_logger import IAuditLogger
from shared.domain.audit import AuditEntry, AuditEvent
from features.connectors.domain.connector_instance import ConnectorInstance
from shared.domain.enums import ConnectorStatus, ConnectorType
from shared.domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError

_log = logging.getLogger(__name__)

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
        *,
        credential_encryptor: ICredentialEncryptor,
        audit_logger: IAuditLogger,
        artifact_probe: IConnectorArtifactProbe,
    ) -> None:
        self._connector_repo = connector_repository
        self._credential_encryptor = credential_encryptor
        self._connector_registry = connector_registry
        self._audit_logger = audit_logger
        self._artifact_probe = artifact_probe


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

        connector_id = uuid4()
        encrypted_credentials = self._credential_encryptor.encrypt(str(config), connector_id)

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
            id=connector_id,
            organization_id=organization_id,
            connector_type=connector_type,
            connector_implementation=connector_implementation,
            name=name,
            encrypted_credentials=encrypted_credentials,
            status=initial_status,
        )
        saved = await self._connector_repo.save(connector)

        self._audit_logger.log(AuditEntry(
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
            connector.encrypted_credentials = self._credential_encryptor.encrypt(str(config), connector.id)

        updated = await self._connector_repo.update(connector)

        self._audit_logger.log(AuditEntry(
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

        from shared.domain.exceptions import ConnectorConnectionFailedError

        connector_impl = self._get_connector_impl(connector.connector_implementation)
        if not connector_impl:
            raise ValidationError(f"Implementación '{connector.connector_implementation}' no soportada")


        connection_ok = False
        try:
            decrypted_config = ast.literal_eval(
                self._credential_encryptor.decrypt(connector.encrypted_credentials, connector.id)
            )
            connection_ok = await connector_impl.test_connection(decrypted_config)
        except Exception as exc:
            _log.error("Connector test failed: id=%s org=%s error=%s", connector_id, connector.organization_id, _redact_exc(exc))

        connector.last_tested_at = datetime.now(timezone.utc)
        connector.status = ConnectorStatus.ACTIVO if connection_ok else ConnectorStatus.ERROR
        updated = await self._connector_repo.update(connector)

        self._audit_logger.log(AuditEntry(
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

        self._audit_logger.log(AuditEntry(
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
        from shared.domain.exceptions import ConnectorConnectionFailedError
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

        try:
            config = ast.literal_eval(
                self._credential_encryptor.decrypt(connector.encrypted_credentials, connector.id)
            )
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
                if re.match(r"^[A-Za-z]\w+-\d+$", query.strip()):
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
            return normalize_browse_items(raw_items, connector.connector_implementation, config)
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

        try:
            config = ast.literal_eval(
                self._credential_encryptor.decrypt(connector.encrypted_credentials, connector.id)
            )
        except Exception as exc:
            _log.error("verify_ref: credential decrypt failed connector_id=%s: %s", connector_id, exc)
            return

        try:
            exists = await self._artifact_probe.exists(connector_impl, external_ref, config)
        except Exception as exc:
            _log.warning(
                "verify_ref: could not verify for connector_id=%s (connectivity issue): %s",
                connector_id, _redact_exc(exc),
            )
            return

        if not exists and connector.status == ConnectorStatus.ACTIVO:
            raise ValidationError(
                f"La referencia externa '{external_ref}' no existe en el conector '{connector.connector_implementation}'. "
                "Verifique que el identificador es correcto y que las credenciales tienen acceso."
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
            plaintext_secret = secrets.token_urlsafe(32)
            connector.webhook_secret_encrypted = self._credential_encryptor.encrypt(plaintext_secret, connector.id)

        connector.webhook_enabled = enabled
        updated = await self._connector_repo.update(connector)

        self._audit_logger.log(AuditEntry(
            event=AuditEvent.CONNECTOR_UPDATED,
            user_id=requested_by,
            organization_id=connector.organization_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"webhook_enabled": enabled},
        ))
        _log.info("Connector webhook configured: id=%s enabled=%s", connector_id, enabled)

        return updated, plaintext_secret
