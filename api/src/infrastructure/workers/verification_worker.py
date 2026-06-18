import uuid
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List

from celery import shared_task
from infrastructure.secondary.queue.celery_app import celery_app
from core.config import settings
from core.pseudonymizer import pseudonymize
from core.email import email_service
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_profile_repository import IProfileRepository
from domain.entities.verification_result import VerificationResult
from domain.enums import ReleaseStatus, VerdictType, SeverityType, severity_to_rule_severity, rule_severity_to_string
from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.secondary.database.repositories.verification_result_repository import SqlVerificationResultRepository
from infrastructure.secondary.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.secondary.database.repositories.user_repository import SqlUserRepository
from infrastructure.secondary.connectors import create_registered_connector_registry


def _map_severity_to_engine(severity: SeverityType) -> str:
    return rule_severity_to_string(severity_to_rule_severity(severity))


def _report_progress(celery_task: Any, current: int, total: int, stage: str) -> None:
    pct = min(99, int(current / total * 100)) if total > 0 else 0
    celery_task.update_state(state='PROGRESS', meta={
        'current': current,
        'total': total,
        'stage': stage,
        'pct': pct,
    })


async def _call_verification_engine(
    artifacts_data: List[Dict[str, Any]],
    rules_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    headers = {}
    if settings.engine_api_key:
        headers["X-Engine-Api-Key"] = settings.engine_api_key
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.engine_url}/api/v1/verify",
            headers=headers,
            json={
                "artifacts": artifacts_data,
                "rules": rules_data,
            },
        )
        response.raise_for_status()
        return response.json()


@celery_app.task(name="infrastructure.workers.verification_worker.run_verification", bind=True)
def run_verification(self, release_id: str) -> Dict[str, Any]:
    release_uuid = uuid.UUID(release_id)

    _report_progress(self, current=0, total=1, stage='loading')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run_verification_async(release_uuid, self.request.id, self))
        return result
    finally:
        loop.close()


async def _run_verification_async(release_id: uuid.UUID, task_id: str, celery_task: Any) -> Dict[str, Any]:
    release_repo = SqlReleaseRepository()
    verification_repo = SqlVerificationResultRepository()
    profile_repo = SqlProfileRepository()
    connector_registry = create_registered_connector_registry()

    release = await release_repo.get_by_id(release_id)
    if not release:
        return {"error": f"Release {release_id} not found"}

    profile = await profile_repo.get_by_id(release.profile_id)
    if not profile:
        return {"error": f"Profile {release.profile_id} not found"}

    artifact_count = len(release.artifacts) if release.artifacts else 0
    # Stages: loading(1) + artifacts(N) + engine(1) + save(1) + notify(1) = N + 4
    total_stages = artifact_count + 4

    _report_progress(celery_task, current=1, total=total_stages, stage='loading')

    artifacts_data = []
    if release.artifacts:
        for i, artifact in enumerate(release.artifacts):
            _report_progress(celery_task, current=2 + i, total=total_stages, stage='fetching_artifacts')
            try:
                connector_impl = connector_registry.get_by_implementation(artifact.connector_implementation)
                if connector_impl:
                    config = {}
                    data = await connector_impl.fetch_artifact(artifact.external_ref, config)
                    data = pseudonymize(data)
                    artifacts_data.append({
                        "id": str(artifact.id),
                        "artifact_type": artifact.artifact_type,
                        "metadata": data,
                    })
            except Exception:
                pass

    rules_data = []
    for rule in profile.rules:
        if rule.is_active:
            rules_data.append({
                "id": str(rule.rule_template),
                "severity": _map_severity_to_engine(rule.severity),
                "params": rule.params,
            })

    engine_stage = 2 + artifact_count
    _report_progress(celery_task, current=engine_stage, total=total_stages, stage='calling_engine')

    try:
        result_data = await _call_verification_engine(artifacts_data, rules_data)
    except Exception as exc:
        await release_repo.update_status(release_id, ReleaseStatus.PENDIENTE)
        raise exc

    verdict_to_status = {
        VerdictType.VALID: ReleaseStatus.VALIDA,
        VerdictType.VALID_WITH_WARNINGS: ReleaseStatus.CON_ADVERTENCIAS,
        VerdictType.INVALID: ReleaseStatus.NO_VALIDA,
    }

    save_stage = engine_stage + 1
    _report_progress(celery_task, current=save_stage, total=total_stages, stage='saving_results')

    verification_result = VerificationResult(
        id=uuid.uuid4(),
        release_id=release_id,
        verdict=result_data["verdict"],
        rule_results=result_data["rule_results"],
        summary=result_data.get("summary", ""),
        executed_at=datetime.now(timezone.utc),
    )

    saved_result = await verification_repo.save(verification_result)
    final_status = verdict_to_status.get(saved_result.verdict, ReleaseStatus.NO_VALIDA)
    await release_repo.update_status(release_id, final_status)

    notify_stage = save_stage + 1
    _report_progress(celery_task, current=notify_stage, total=total_stages, stage='notifying')

    user_repo = SqlUserRepository()
    user = await user_repo.get_by_id(release.created_by)
    if user:
        try:
            await email_service.send_verification_result_email(
                to_email=user.email,
                to_name=user.display_name or user.email,
                release_name=release.name,
                verdict=saved_result.verdict.value,
                release_id=str(release_id),
            )
        except Exception:
            pass

    return {
        "result_id": str(saved_result.id),
        "release_id": str(release_id),
        "verdict": saved_result.verdict.value,
        "summary": saved_result.summary,
        "task_id": task_id,
    }
