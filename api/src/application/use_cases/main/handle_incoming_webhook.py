import json
from typing import Mapping, Optional
from uuid import UUID

from cryptography.fernet import Fernet

from application.ports.input.i_release_service import IReleaseService
from application.ports.input.i_verification_service import IVerificationService
from application.ports.output.i_connector_repository import IConnectorRepository
from application.ports.output.i_organization_repository import IOrganizationRepository
from application.ports.output.i_project_repository import IProjectRepository
from application.use_cases.main.webhook_payload_parser import (
    event_header_name,
    parse_tag_push_event,
    version_from_tag_name,
)
from core.config import settings
from core.logger import get_logger
from core.webhook_signature import signature_header_name, verify_webhook_signature
from domain.exceptions import EntityNotFoundError, InvalidWebhookSignatureError, ValidationError

_log = get_logger(__name__)


class HandleIncomingWebhookUseCase:
    """Recibe un webhook de un conector REPO_CODIGO (GitHub/GitLab/Gitea/
    Bitbucket), verifica su firma, y si el evento es la creación de un tag/
    release, crea la Release + Artifact correspondientes en SVAES y lanza su
    verificación automáticamente - cerrando el ciclo manual de "crear release
    y pulsar verificar" para equipos que ya etiquetan sus versiones en su
    repositorio de código.
    """

    def __init__(
        self,
        connector_repository: IConnectorRepository,
        project_repository: IProjectRepository,
        organization_repository: IOrganizationRepository,
        release_service: IReleaseService,
        verification_service: IVerificationService,
    ) -> None:
        self._connector_repo = connector_repository
        self._project_repo = project_repository
        self._organization_repo = organization_repository
        self._release_service = release_service
        self._verification_service = verification_service

    async def handle_source_control_event(
        self,
        project_id: UUID,
        connector_id: UUID,
        raw_body: bytes,
        headers: Mapping[str, str],
    ) -> Optional[UUID]:
        """Devuelve el UUID de la release creada, o None si el evento fue
        aceptado pero no representaba un tag/release nuevo (no hay nada que
        verificar, no es un error)."""
        connector = await self._connector_repo.get_by_id(connector_id)
        if not connector:
            raise EntityNotFoundError(f"Conector no encontrado: {connector_id}")
        if not connector.webhook_enabled or connector.connector_type != "REPO_CODIGO":
            raise ValidationError("El webhook de este conector no está habilitado.")
        if not connector.webhook_secret_encrypted:
            raise ValidationError("El conector no tiene un secreto de webhook configurado.")

        project = await self._project_repo.get_by_id(project_id)
        if not project or project.organization_id != connector.organization_id:
            raise EntityNotFoundError(f"Proyecto no encontrado: {project_id}")

        fernet = Fernet(settings.encryption_key.encode())  # pyright: ignore[reportOptionalMemberAccess]
        secret = fernet.decrypt(connector.webhook_secret_encrypted).decode()

        header_name = signature_header_name(connector.connector_implementation)
        header_value = headers.get(header_name) if header_name else None
        if not verify_webhook_signature(connector.connector_implementation, secret, raw_body, header_value):
            raise InvalidWebhookSignatureError("Firma de webhook inválida.")

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("El cuerpo del webhook no es JSON válido.")

        event_header = headers.get(event_header_name(connector.connector_implementation) or "")
        event = parse_tag_push_event(connector.connector_implementation, event_header, payload)
        if event is None:
            _log.info(
                "Webhook accepted but not a tag/release event: connector=%s project=%s event=%s",
                connector_id, project_id, event_header,
            )
            return None

        organization = await self._organization_repo.get_by_id(connector.organization_id)
        if not organization or not organization.owner_id:
            raise ValidationError("La organización no tiene un propietario asignado.")
        actor_id = organization.owner_id

        release = await self._release_service.create_release(
            name=f"{project.name} {event.tag_name}",
            version=version_from_tag_name(event.tag_name),
            project_id=project_id,
            user_id=actor_id,
            description=f"Creada automáticamente desde el webhook de {connector.connector_implementation} (tag {event.tag_name}).",
        )
        await self._release_service.add_artifact(
            release_id=release.id,
            connector_instance_id=connector_id,
            connector_implementation=connector.connector_implementation,
            artifact_type="CODIGO",
            external_ref=event.external_ref,
        )
        await self._verification_service.launch_verification(release_id=release.id, requested_by=actor_id)
        _log.info("Release auto-created and verification launched from webhook: release=%s project=%s", release.id, project_id)

        return release.id
