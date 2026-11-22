from typing import Any

import httpx

from features.verification.application.ports.i_verification_engine import IVerificationEngine
from features.projects_releases.domain.release import Release
from features.verification.domain.verification_profile import VerificationProfile
from features.verification.domain.verification_result import VerificationResult
from shared.domain.enums import VerdictType, rule_severity_to_string, severity_to_rule_severity


_ENGINE_VERDICT_MAP = {
    "VALIDA": VerdictType.VALID,
    "CON_ADVERTENCIAS": VerdictType.VALID_WITH_WARNINGS,
    "NO_VALIDA": VerdictType.INVALID,
}


class HttpRuleEngineClient(IVerificationEngine):
    def __init__(self, url: str, api_key: str | None) -> None:
        self._url = url
        self._api_key = api_key

    async def execute_verification(
        self, release: Release, profile: VerificationProfile, artifacts_data: list[dict[str, Any]],
    ) -> VerificationResult:
        rules_data = [
            {
                "id": str(rule.rule_template),
                "severity": rule_severity_to_string(severity_to_rule_severity(rule.severity)),
                "params": rule.params,
            }
            for rule in profile.rules
            if rule.is_active
        ]
        result = await self.verify(artifacts_data, rules_data, release.version)
        return VerificationResult(
            release_id=release.id,
            verdict=_ENGINE_VERDICT_MAP.get(result.get("verdict"), VerdictType.INVALID),
            rule_results=result.get("rule_results", []),
            summary=result.get("summary", {}),
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self._url}/health")
            return response.is_success
        except httpx.RequestError:
            return False

    async def verify(
        self,
        artifacts_data: list[dict[str, Any]],
        rules_data: list[dict[str, Any]],
        release_version: str | None = None,
    ) -> dict[str, Any]:
        headers = {}
        if self._api_key:
            headers["X-Engine-Api-Key"] = self._api_key
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._url}/api/v1/verify",
                headers=headers,
                json={
                    "artifacts": artifacts_data,
                    "rules": rules_data,
                    "release_version": release_version,
                },
            )
            response.raise_for_status()
            return response.json()
