import ast
import uuid
import asyncio
import logging
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
from infrastructure.secondary.database.repositories.notification_repository import SqlNotificationRepository
from infrastructure.secondary.connectors import create_registered_connector_registry
from infrastructure.secondary.database.repositories.connector_repository import SqlConnectorRepository
from core.rule_names import RULE_NAMES, RULE_DEFAULT_ARTIFACT_TYPES, RULE_CONNECTOR_TYPES


RULE_OK_EVIDENCE: dict[str, str] = {
    "RV-01": "rule_evidence.ok.RV-01",
    "RV-02": "rule_evidence.ok.RV-02",
    "RV-03": "rule_evidence.ok.RV-03",
    "RV-04": "rule_evidence.ok.RV-04",
    "RV-05": "rule_evidence.ok.RV-05",
    "RV-06": "rule_evidence.ok.RV-06",
    "RV-07": "rule_evidence.ok.RV-07",
    "RV-08": "rule_evidence.ok.RV-08",
    "RV-09": "rule_evidence.ok.RV-09",
    "RV-10": "rule_evidence.ok.RV-10",
    "has_duplicated_code": "rule_evidence.ok.has_duplicated_code",
    "has_high_severity_vulnerabilities": "rule_evidence.ok.has_high_severity_vulnerabilities",
    "has_critical_vulnerabilities": "rule_evidence.ok.has_critical_vulnerabilities",
    "has_open_high_priority_issues": "rule_evidence.ok.has_open_high_priority_issues",
    "has_code_smells": "rule_evidence.ok.has_code_smells",
    "has_security_hotspots": "rule_evidence.ok.has_security_hotspots",
    "has_uncovered_code": "rule_evidence.ok.has_uncovered_code",
    "has_blocking_issues": "rule_evidence.ok.has_blocking_issues",
    "meets_minimum_test_coverage": "rule_evidence.ok.meets_minimum_test_coverage",
    "meets_maximum_complexity": "rule_evidence.ok.meets_maximum_complexity",
}


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


async def _fetch_artifacts(
    artifacts: list,
    connector_registry: Any,
    celery_task: Any,
    total_stages: int,
) -> tuple[list, list]:
    from cryptography.fernet import Fernet
    connector_repo = SqlConnectorRepository()
    fernet = Fernet(settings.encryption_key.encode())  # type: ignore[union-attr]
    artifacts_data = []
    fetch_errors = []
    for i, artifact in enumerate(artifacts):
        _report_progress(celery_task, current=2 + i, total=total_stages, stage='fetching_artifacts')
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
            config = ast.literal_eval(fernet.decrypt(connector_instance.encrypted_credentials).decode())
            data = await connector_impl.fetch_artifact(artifact.external_ref, config)
            data = pseudonymize(data)
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


def _build_rules_data(profile: Any) -> list:
    rules_data = []
    for rule in profile.rules:
        if rule.is_active:
            rules_data.append({
                "id": str(rule.rule_template),
                "severity": _map_severity_to_engine(rule.severity),
                "params": rule.params,
            })
    return rules_data


_ENGINE_VERDICT_MAP = {
    "VALIDA": VerdictType.VALID,
    "CON_ADVERTENCIAS": VerdictType.VALID_WITH_WARNINGS,
    "NO_VALIDA": VerdictType.INVALID,
}

_VERDICT_TO_STATUS = {
    VerdictType.VALID: ReleaseStatus.VALIDA,
    VerdictType.VALID_WITH_WARNINGS: ReleaseStatus.CON_ADVERTENCIAS,
    VerdictType.INVALID: ReleaseStatus.NO_VALIDA,
}

_wlog = logging.getLogger(__name__)


async def _add_connector_name(
    connector_repo: Any,
    connector_names: dict[uuid.UUID, str],
    seen: set[uuid.UUID],
    connector_instance_id: uuid.UUID,
) -> None:
    if connector_instance_id and connector_instance_id not in seen:
        seen.add(connector_instance_id)
        connector = await connector_repo.get_by_id(connector_instance_id)
        if connector:
            connector_names[connector_instance_id] = connector.name


async def _build_connector_names(profile: Any, release_artifacts: list | None = None) -> dict:
    connector_repo = SqlConnectorRepository()
    connector_names: dict[uuid.UUID, str] = {}
    seen: set[uuid.UUID] = set()

    for rule in profile.rules:
        await _add_connector_name(connector_repo, connector_names, seen, rule.connector_instance_id)

    if release_artifacts:
        for artifact in release_artifacts:
            await _add_connector_name(connector_repo, connector_names, seen, artifact.connector_instance_id)

    return connector_names


async def _build_artifact_type_connector_map(release_artifacts: list) -> dict[str, str]:
    connector_repo = SqlConnectorRepository()
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


def _get_artifact_fetch_error_connector(
    rule_result: dict, connector_names: dict
) -> str:
    ciid_str = rule_result.get("connector_instance_id", "")
    if ciid_str:
        try:
            return connector_names.get(uuid.UUID(ciid_str), "")
        except (ValueError, KeyError):
            return ""
    return ""


def _get_artifact_type_fallback(
    rid: str, rule_lookup: dict, artifact_type_connector: dict[str, str]
) -> str:
    profile_rule = rule_lookup.get(rid)
    params = profile_rule.params if profile_rule else {}
    artifact_type = params.get("artifact_type") or RULE_DEFAULT_ARTIFACT_TYPES.get(rid)
    if artifact_type:
        return artifact_type_connector.get(artifact_type, "")
    return ""


def _get_connector_for_rule(
    rid: str,
    rule_result: dict,
    rule_lookup: dict,
    connector_names: dict,
    artifact_type_connector: dict[str, str] | None = None,
) -> str:
    if rid == "artifact_fetch_error":
        return _get_artifact_fetch_error_connector(rule_result, connector_names)

    profile_rule = rule_lookup.get(rid)
    if profile_rule and profile_rule.connector_instance_id:
        name = connector_names.get(profile_rule.connector_instance_id, "")
        if name:
            return name

    if artifact_type_connector:
        return _get_artifact_type_fallback(rid, rule_lookup, artifact_type_connector)

    return ""


def _enrich_rule_results(
    result_data: dict,
    rule_lookup: dict,
    connector_names: dict,
    artifact_type_connector: dict[str, str] | None = None,
) -> None:
    for rule_result in result_data.get("rule_results", []):
        rid = rule_result.get("rule_id", "")
        rule_result["rule_name"] = RULE_NAMES.get(rid, rid)

        if rid == "RV-01":
            # RV-01 checks artifact existence — no connector involved; always show dash
            rule_result["connector"] = "-"
        else:
            connector = _get_connector_for_rule(
                rid, rule_result, rule_lookup, connector_names, artifact_type_connector
            )
            rule_result["connector"] = connector
            # A rule with no linked artifact cannot be OK or ERROR: mark not evaluated
            if (not connector
                    and rule_result.get("status") in ("OK", "ERROR")
                    and rid != "artifact_fetch_error"):
                rule_result["status"] = "NO_EVALUADA"
                rule_result["message"] = "rule_evidence.no_connector"
                rule_result["message_params"] = None

        rule_result["evidence"] = rule_result.get("message", "")
        rule_result["evidence_params"] = rule_result.get("message_params")
        if not rule_result["evidence"] and rule_result.get("status") == "OK":
            rule_result["evidence"] = RULE_OK_EVIDENCE.get(rid, "rule_evidence.ok.default")
            rule_result["evidence_params"] = None


async def _notify_user(release_id: uuid.UUID, release: Any, saved_result: Any) -> None:
    user_repo = SqlUserRepository()
    user = await user_repo.get_by_id(release.created_by)
    if not user:
        _wlog.warning("Cannot notify: user not found for release %s (created_by=%s)", release_id, release.created_by)
        return

    verdict_value = saved_result.verdict.value
    if verdict_value in ("VALID", "VALID_WITH_WARNINGS"):
        event_type = "RELEASE_VALIDATED"
    else:
        event_type = "RELEASE_INVALIDATED"

    notification_repo = SqlNotificationRepository()
    subscription = await notification_repo.get_subscription(user.id, event_type)
    if subscription is not None and not subscription.enabled:
        _wlog.info("Skipping notification for release %s: user %s has disabled %s", release_id, user.id, event_type)
        return

    try:
        await email_service.send_verification_result_email(
            to_email=user.email,
            to_name=user.display_name or user.email,
            release_name=release.name,
            verdict=verdict_value,
            release_id=str(release_id),
        )
    except Exception:
        _wlog.exception("Failed to send verification email for release %s to %s", release_id, user.email)


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
    total_stages = artifact_count + 4

    _report_progress(celery_task, current=1, total=total_stages, stage='loading')

    artifacts_data, fetch_errors = await _fetch_artifacts(
        release.artifacts or [], connector_registry, celery_task, total_stages
    )

    rules_data = _build_rules_data(profile)

    engine_stage = 2 + artifact_count
    _report_progress(celery_task, current=engine_stage, total=total_stages, stage='calling_engine')

    try:
        result_data = await _call_verification_engine(artifacts_data, rules_data)
    except Exception as exc:
        await release_repo.update_status(release_id, ReleaseStatus.PENDIENTE)
        raise exc

    rule_lookup = {rule.rule_template: rule for rule in profile.rules}
    connector_names = await _build_connector_names(profile, release.artifacts or [])
    artifact_type_connector = await _build_artifact_type_connector_map(release.artifacts or [])

    for fe in fetch_errors:
        ref = fe.get("external_ref") or fe["artifact_id"]
        result_data.setdefault("rule_results", []).append({
            "rule_id": "artifact_fetch_error",
            "rule_name": "Error al recuperar artefacto",
            "status": "WARNING",
            "message": "rule_evidence.warning.artifact_fetch_error",
            "message_params": {
                "ref": ref,
                "artifact_type": fe["artifact_type"],
                "connector": fe["connector"],
                "error": fe["error"],
            },
            "connector": fe["connector"],
            "connector_instance_id": fe.get("connector_instance_id", ""),
            "evidence": "rule_evidence.warning.artifact_fetch_error.evidence",
            "evidence_params": {
                "ref": ref,
                "artifact_type": fe["artifact_type"],
                "connector": fe["connector"],
            },
        })

    _enrich_rule_results(result_data, rule_lookup, connector_names, artifact_type_connector)

    save_stage = engine_stage + 1
    _report_progress(celery_task, current=save_stage, total=total_stages, stage='saving_results')

    raw_verdict = result_data.get("verdict", "NO_VALIDA")
    domain_verdict = _ENGINE_VERDICT_MAP.get(raw_verdict, VerdictType.INVALID)

    verification_result = VerificationResult(
        id=uuid.uuid4(),
        release_id=release_id,
        verdict=domain_verdict,
        rule_results=result_data.get("rule_results", []),
        summary=result_data.get("summary", {}),
        executed_at=datetime.now(timezone.utc),
    )

    try:
        saved_result = await verification_repo.save(verification_result)
        final_status = _VERDICT_TO_STATUS.get(saved_result.verdict, ReleaseStatus.NO_VALIDA)
        await release_repo.update_status(release_id, final_status)
    except Exception as exc:
        await release_repo.update_status(release_id, ReleaseStatus.PENDIENTE)
        raise exc

    notify_stage = save_stage + 1
    _report_progress(celery_task, current=notify_stage, total=total_stages, stage='notifying')

    await _notify_user(release_id, release, saved_result)

    return {
        "result_id": str(saved_result.id),
        "release_id": str(release_id),
        "verdict": saved_result.verdict.value,
        "summary": saved_result.summary,
        "task_id": task_id,
    }
