import ast
import logging
import uuid
from collections.abc import Callable
from typing import Any

from features.connectors.application.ports.i_connector_registry import IConnectorRegistry
from features.connectors.application.ports.i_connector_repository import IConnectorRepository
from shared.application.i_credential_encryptor import ICredentialEncryptor
from features.verification.application.pseudonymizer import pseudonymize


_wlog = logging.getLogger(__name__)


async def fetch_artifacts(
    connector_repo: IConnectorRepository,
    credential_encryptor: ICredentialEncryptor,
    artifacts: list,
    connector_registry: IConnectorRegistry,
    report_progress: Callable[[int, int, str], None],
    total_stages: int,
) -> tuple[list, list]:
    artifacts_data = []
    fetch_errors = []
    for i, artifact in enumerate(artifacts):
        report_progress(2 + i, total_stages, "fetching_artifacts")
        try:
            connector_impl = connector_registry.get_by_implementation(artifact.connector_implementation)
            connector_instance = await connector_repo.get_by_id(artifact.connector_instance_id)
            if not connector_instance:
                _wlog.warning(
                    "Connector instance %s not found for artifact %s",
                    artifact.connector_instance_id, artifact.id,
                )
                fetch_errors.append({
                    "artifact_id": str(artifact.id),
                    "external_ref": artifact.external_ref,
                    "artifact_type": artifact.artifact_type,
                    "connector": artifact.connector_implementation,
                    "connector_instance_id": str(artifact.connector_instance_id),
                    "error": f"Instancia de conector {artifact.connector_instance_id} no encontrada",
                })
                continue
            config = ast.literal_eval(
                credential_encryptor.decrypt(connector_instance.encrypted_credentials, connector_instance.id)
            )
            data = await connector_impl.fetch_artifact(artifact.external_ref, config)
            data = pseudonymize(data)
            # Reglas como RV-08 necesitan comparar contra la referencia externa que
            # el usuario introdujo al importar el artefacto (p. ej. "SVAES-1"), no
            # contra el UUID interno de SVAES, que ninguna herramienta externa puede
            # conocer ni declarar en un campo de "tareas planificadas".
            data["_svaes_external_ref"] = artifact.external_ref
            artifacts_data.append({
                "id": str(artifact.id),
                "artifact_type": artifact.artifact_type,
                "metadata": data,
            })
        except Exception as exc:
            _wlog.exception(
                "Failed to fetch artifact %s (connector=%s, ref=%s)",
                artifact.id, artifact.connector_implementation, artifact.external_ref,
            )
            fetch_errors.append({
                "artifact_id": str(artifact.id),
                "external_ref": artifact.external_ref,
                "artifact_type": artifact.artifact_type,
                "connector": artifact.connector_implementation,
                "connector_instance_id": str(artifact.connector_instance_id),
                "error": str(exc),
            })
    return artifacts_data, fetch_errors


async def _add_connector_name(
    connector_repo: IConnectorRepository,
    connector_names: dict[uuid.UUID, str],
    seen: set[uuid.UUID],
    connector_instance_id: uuid.UUID,
) -> None:
    if connector_instance_id and connector_instance_id not in seen:
        seen.add(connector_instance_id)
        connector = await connector_repo.get_by_id(connector_instance_id)
        if connector:
            connector_names[connector_instance_id] = connector.name


async def build_connector_names(
    connector_repo: IConnectorRepository, profile: Any, release_artifacts: list | None = None,
) -> dict:
    connector_names: dict[uuid.UUID, str] = {}
    seen: set[uuid.UUID] = set()

    for rule in profile.rules:
        await _add_connector_name(connector_repo, connector_names, seen, rule.connector_instance_id)

    if release_artifacts:
        for artifact in release_artifacts:
            await _add_connector_name(connector_repo, connector_names, seen, artifact.connector_instance_id)

    return connector_names


async def build_artifact_type_connector_map(
    connector_repo: IConnectorRepository, release_artifacts: list,
) -> dict[str, str]:
    artifact_type_to_connector: dict[str, str] = {}
    connector_cache: dict[uuid.UUID, str] = {}
    for artifact in release_artifacts:
        if not artifact.connector_instance_id:
            continue
        if artifact.artifact_type in artifact_type_to_connector:
            continue
        cid = artifact.connector_instance_id
        if cid not in connector_cache:
            connector = await connector_repo.get_by_id(cid)
            connector_cache[cid] = connector.name if connector else ""
        name = connector_cache.get(cid, "")
        if name:
            artifact_type_to_connector[artifact.artifact_type] = name
    return artifact_type_to_connector


async def build_connector_type_map(
    connector_repo: IConnectorRepository, release_artifacts: list,
) -> dict[str, str]:
    connector_type_to_name: dict[str, str] = {}
    connector_cache: dict[uuid.UUID, Any] = {}
    for artifact in release_artifacts:
        cid = artifact.connector_instance_id
        if not cid:
            continue
        if cid not in connector_cache:
            connector_cache[cid] = await connector_repo.get_by_id(cid)
        connector = connector_cache[cid]
        if connector and connector.connector_type not in connector_type_to_name:
            connector_type_to_name[connector.connector_type] = connector.name
    return connector_type_to_name
