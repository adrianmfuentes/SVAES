import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from features.connectors.application.ports.i_connector_registry import IConnectorRegistry
from features.connectors.application.ports.i_connector_repository import IConnectorRepository
from shared.application.i_credential_encryptor import ICredentialEncryptor
from features.verification.application.ports.i_profile_repository import IProfileRepository
from features.projects_releases.application.ports.i_release_repository import IReleaseRepository
from features.verification.application.ports.i_verification_engine import IVerificationEngine
from features.verification.application.ports.i_verification_outcome_store import IVerificationOutcomeStore
from features.projects_releases.domain.release import Release
from features.verification.domain.verification_result import VerificationResult
from shared.domain.enums import ReleaseStatus, VerdictType
from features.verification.application.connector_artifacts import (
    build_artifact_type_connector_map,
    build_connector_names,
    build_connector_type_map,
    fetch_artifacts,
)
from features.verification.application.rule_results import _enrich_rule_results, _recompute_verdict
from shared.application.i_clock import IClock


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

class RunVerification:
    def __init__(
        self, *, releases: IReleaseRepository, outcomes: IVerificationOutcomeStore,
        profiles: IProfileRepository, connectors: IConnectorRepository,
        registry: IConnectorRegistry, encryptor: ICredentialEncryptor,
        engine: IVerificationEngine, clock: IClock,
        notify: Callable[[uuid.UUID, Release, VerificationResult, str], Awaitable[None]],
    ) -> None:
        self._releases = releases
        self._outcomes = outcomes
        self._profiles = profiles
        self._connectors = connectors
        self._registry = registry
        self._encryptor = encryptor
        self._engine = engine
        self._clock = clock
        self._notify = notify

    async def execute(
        self, release_id: uuid.UUID, task_id: str, triggered_by: str,
        report_progress: Callable[[int, int, str], None],
    ) -> dict[str, Any]:
        release = await self._releases.get_by_id(release_id)
        if not release:
            return {"error": f"Release {release_id} not found"}

        profile = await self._profiles.get_by_id(release.profile_id)
        if not profile:
            return {"error": f"Profile {release.profile_id} not found"}

        artifact_count = len(release.artifacts) if release.artifacts else 0
        total_stages = artifact_count + 4

        report_progress(1, total_stages, 'loading')

        artifacts_data, fetch_errors = await fetch_artifacts(
            self._connectors, self._encryptor, release.artifacts or [], self._registry, report_progress, total_stages
        )

        engine_stage = 2 + artifact_count
        report_progress(engine_stage, total_stages, 'calling_engine')

        try:
            engine_result = await self._engine.execute_verification(release, profile, artifacts_data)
        except Exception:
            await self._releases.update_status(release_id, ReleaseStatus.PENDIENTE)
            raise

        result_data = {"rule_results": engine_result.rule_results}
        rule_lookup = {rule.rule_template: rule for rule in profile.rules}
        connector_names = await build_connector_names(self._connectors, profile, release.artifacts or [])
        artifact_type_connector = await build_artifact_type_connector_map(self._connectors, release.artifacts or [])
        connector_type_map = await build_connector_type_map(self._connectors, release.artifacts or [])

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

        _enrich_rule_results(result_data, rule_lookup, connector_names, artifact_type_connector, connector_type_map)

        active_rules = [rule for rule in profile.rules if rule.is_active]
        engine_rule_results = result_data.get("rule_results", [])[:len(active_rules)]
        result_data["verdict"] = _recompute_verdict(engine_rule_results, active_rules)

        save_stage = engine_stage + 1
        report_progress(save_stage, total_stages, 'saving_results')

        raw_verdict = result_data.get("verdict", "NO_VALIDA")
        domain_verdict = _ENGINE_VERDICT_MAP.get(raw_verdict, VerdictType.INVALID)

        verification_result = VerificationResult(
            id=uuid.uuid4(),
            release_id=release_id,
            verdict=domain_verdict,
            rule_results=result_data.get("rule_results", []),
            summary=engine_result.summary,
            executed_at=self._clock.now(),
        )

        try:
            final_status = _VERDICT_TO_STATUS[domain_verdict]
            saved_result = await self._outcomes.save(verification_result, final_status)
        except Exception:
            await self._releases.update_status(release_id, ReleaseStatus.PENDIENTE)
            raise

        notify_stage = save_stage + 1
        report_progress(notify_stage, total_stages, 'notifying')

        await self._notify(release_id, release, saved_result, triggered_by)

        return {
            "result_id": str(saved_result.id),
            "release_id": str(release_id),
            "verdict": saved_result.verdict.value,
            "summary": saved_result.summary,
            "task_id": task_id,
        }
