import uuid
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List

from celery import shared_task
from infrastructure.secondary.queue.celery_app import celery_app
from core.config import settings
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_connector_registry import IConnectorRegistry
from domain.entities.verification_result import VerificationResult
from domain.enums import ReleaseStatus, VerdictType, SeverityType
from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.secondary.database.repositories.verification_result_repository import SqlVerificationResultRepository
from infrastructure.secondary.connectors import create_registered_connector_registry


async def _fetch_artifacts_via_connectors(
    release_id: str,
    connector_registry: IConnectorRegistry,
) -> List[Dict[str, Any]]:
    return []


async def _call_verification_engine(
    release_id: str,
    artifacts_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.engine_url}/api/v1/verify",
            json={
                "release_id": release_id,
                "artifacts": artifacts_data,
            },
        )
        response.raise_for_status()
        return response.json()


@celery_app.task(name="infrastructure.workers.verification_worker.run_verification", bind=True)
def run_verification(self, release_id: str) -> Dict[str, Any]:
    release_uuid = uuid.UUID(release_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run_verification_async(release_uuid, self.request.id))
        return result
    finally:
        loop.close()


async def _run_verification_async(release_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    release_repo = SqlReleaseRepository()
    verification_repo = SqlVerificationResultRepository()
    connector_registry = create_registered_connector_registry()

    release = await release_repo.get_by_id(release_id)
    if not release:
        return {"error": f"Release {release_id} not found"}

    artifacts_data = []
    if release.artifacts:
        for artifact in release.artifacts:
            try:
                connector_impl = connector_registry.get_by_implementation(artifact.connector_implementation)
                if connector_impl:
                    config = {}
                    data = await connector_impl.fetch_artifact(artifact.external_ref, config)
                    artifacts_data.append({
                        "artifact_id": str(artifact.id),
                        "type": artifact.artifact_type,
                        "external_ref": artifact.external_ref,
                        "connector_impl": artifact.connector_implementation,
                        "data": data,
                    })
            except Exception:
                pass

    result_data = await _call_verification_engine(str(release_id), artifacts_data)

    verification_result = VerificationResult(
        id=uuid.uuid4(),
        release_id=release_id,
        verdict=result_data["verdict"],
        rule_results=result_data["rule_results"],
        summary=result_data["summary"],
        executed_at=datetime.now(timezone.utc),
    )

    saved_result = await verification_repo.save(verification_result)
    await release_repo.update_status(release_id, ReleaseStatus.EN_VERIFICACION)

    return {
        "result_id": str(saved_result.id),
        "release_id": str(release_id),
        "verdict": saved_result.verdict.value,
        "summary": saved_result.summary,
        "task_id": task_id,
    }