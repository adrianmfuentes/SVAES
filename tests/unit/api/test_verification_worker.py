import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from infrastructure.workers.verification_worker import (
    _run_verification_async,
    _map_severity_to_engine,
    _call_verification_engine,
)
from domain.entities.release import Release
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.entities.artifact import Artifact
from domain.enums import ReleaseStatus, SeverityType, VerdictType, RuleSeverityType

pytestmark = pytest.mark.unit


class TestMapSeverityToEngine:
    def test_critical_maps_to_obligatoria(self):
        """Verifica que CRITICAL se mapee a OBLIGATORIA."""
        assert _map_severity_to_engine(SeverityType.CRITICAL) == "OBLIGATORIA"

    def test_high_maps_to_obligatoria(self):
        """Verifica que HIGH se mapee a OBLIGATORIA."""
        assert _map_severity_to_engine(SeverityType.HIGH) == "OBLIGATORIA"

    def test_medium_maps_to_opcional(self):
        """Verifica que MEDIUM se mapee a OPCIONAL."""
        assert _map_severity_to_engine(SeverityType.MEDIUM) == "OPCIONAL"

    def test_low_maps_to_opcional(self):
        """Verifica que LOW se mapee a OPCIONAL."""
        assert _map_severity_to_engine(SeverityType.LOW) == "OPCIONAL"

    def test_info_maps_to_opcional(self):
        """Verifica que INFO se mapee a OPCIONAL."""
        assert _map_severity_to_engine(SeverityType.INFO) == "OPCIONAL"


class TestCallVerificationEngine:
    @pytest.mark.asyncio
    async def test_call_engine_success(self):
        """Verifica la llamada exitosa al motor de verificación."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "verdict": "VALID",
            "rule_results": [{"rule": "check_1", "status": "passed"}],
            "summary": "All checks passed",
        }

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("infrastructure.workers.verification_worker.settings") as mock_settings:
                mock_settings.engine_url = "http://engine:8000"
                mock_settings.engine_api_key = "test-key"

                result = await _call_verification_engine(
                    artifacts_data=[{"id": "a1", "type": "code", "metadata": {}}],
                    rules_data=[{"id": "check_1", "severity": "OBLIGATORIA", "params": {}}],
                )

                assert result["verdict"] == "VALID"
                assert len(result["rule_results"]) == 1
                assert result["summary"] == "All checks passed"

    @pytest.mark.asyncio
    async def test_call_engine_no_api_key(self):
        """Verifica la llamada al motor sin API key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"verdict": "VALID", "rule_results": [], "summary": ""}

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("infrastructure.workers.verification_worker.settings") as mock_settings:
                mock_settings.engine_url = "http://engine:8000"
                mock_settings.engine_api_key = None

                await _call_verification_engine([], [])

                call_kwargs = mock_client.post.call_args
                assert "X-Engine-Api-Key" not in call_kwargs[1].get("headers", {})


class TestRunVerificationAsync:
    @pytest.mark.asyncio
    async def test_release_not_found(self):
        """Verifica que se retorne error cuando la release no existe."""
        release_id = uuid4()
        task_id = "task-123"

        with patch(
            "infrastructure.workers.verification_worker.SqlReleaseRepository"
        ) as mock_release_repo_class:
            mock_release_repo = AsyncMock()
            mock_release_repo.get_by_id = AsyncMock(return_value=None)
            mock_release_repo_class.return_value = mock_release_repo

            result = await _run_verification_async(release_id, task_id)

            assert "error" in result
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_profile_not_found(self):
        """Verifica que se retorne error cuando el perfil no existe."""
        release_id = uuid4()
        task_id = "task-123"

        release = Release(
            id=release_id,
            name="Test",
            version="1.0.0",
            project_id=uuid4(),
            profile_id=uuid4(),
            created_by=uuid4(),
            status=ReleaseStatus.EN_VERIFICACION,
        )

        with patch(
            "infrastructure.workers.verification_worker.SqlReleaseRepository"
        ) as mock_release_repo_class:
            with patch(
                "infrastructure.workers.verification_worker.SqlProfileRepository"
            ) as mock_profile_repo_class:
                mock_release_repo = AsyncMock()
                mock_release_repo.get_by_id = AsyncMock(return_value=release)
                mock_release_repo_class.return_value = mock_release_repo

                mock_profile_repo = AsyncMock()
                mock_profile_repo.get_by_id = AsyncMock(return_value=None)
                mock_profile_repo_class.return_value = mock_profile_repo

                result = await _run_verification_async(release_id, task_id)

                assert "error" in result
                assert "Profile" in result["error"]

    @pytest.mark.asyncio
    async def test_full_verification_flow(self):
        """Verifica el flujo completo de verificación exitosa."""
        release_id = uuid4()
        profile_id = uuid4()
        task_id = "task-123"

        release = Release(
            id=release_id,
            name="Test Release",
            version="1.0.0",
            project_id=uuid4(),
            profile_id=profile_id,
            created_by=uuid4(),
            status=ReleaseStatus.EN_VERIFICACION,
        )
        artifact = Artifact(
            id=uuid4(),
            release_id=release_id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="https://gitlab.com/repo/commit/abc",
        )
        release.artifacts = [artifact]

        rule = VerificationRule(
            profile_id=profile_id,
            rule_template="check_unit_tests",
            severity=SeverityType.HIGH,
            params={"min_coverage": 80},
            is_active=True,
        )
        profile = VerificationProfile(
            id=profile_id,
            organization_id=uuid4(),
            name="Test Profile",
            description="",
            is_default=False,
            rules=[rule],
        )

        engine_result = {
            "verdict": "VALID",
            "rule_results": [{"rule": "check_1", "status": "passed"}],
            "summary": "All ok",
        }

        with patch(
            "infrastructure.workers.verification_worker.SqlReleaseRepository"
        ) as mock_release_repo_class:
            with patch(
                "infrastructure.workers.verification_worker.SqlProfileRepository"
            ) as mock_profile_repo_class:
                with patch(
                    "infrastructure.workers.verification_worker.SqlVerificationResultRepository"
                ) as mock_ver_repo_class:
                    with patch(
                        "infrastructure.workers.verification_worker.create_registered_connector_registry"
                    ) as mock_registry_fn:
                        with patch(
                            "infrastructure.workers.verification_worker._call_verification_engine"
                        ) as mock_engine:
                            mock_release_repo = AsyncMock()
                            mock_release_repo.get_by_id = AsyncMock(return_value=release)
                            mock_release_repo.update_status = AsyncMock()
                            mock_release_repo_class.return_value = mock_release_repo

                            mock_profile_repo = AsyncMock()
                            mock_profile_repo.get_by_id = AsyncMock(return_value=profile)
                            mock_profile_repo_class.return_value = mock_profile_repo

                            saved_result = MagicMock()
                            saved_result.id = uuid4()
                            saved_result.verdict = VerdictType.VALID
                            saved_result.summary = "All ok"

                            mock_ver_repo = AsyncMock()
                            mock_ver_repo.save = AsyncMock(return_value=saved_result)
                            mock_ver_repo_class.return_value = mock_ver_repo

                            mock_connector = AsyncMock()
                            mock_connector.fetch_artifact = AsyncMock(return_value={"key": "value"})
                            mock_registry = MagicMock()
                            mock_registry.get_by_implementation = MagicMock(return_value=mock_connector)
                            mock_registry_fn.return_value = mock_registry

                            mock_engine.return_value = engine_result

                            result = await _run_verification_async(release_id, task_id)

                            assert result["release_id"] == str(release_id)
                            assert result["verdict"] == "VALID"
                            assert result["summary"] == "All ok"
                            assert result["task_id"] == task_id
                            mock_ver_repo.save.assert_called_once()
                            mock_release_repo.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_verification_with_inactive_rules_skipped(self):
        """Verifica que las reglas inactivas se omitan."""
        release_id = uuid4()
        profile_id = uuid4()
        task_id = "task-123"

        release = Release(
            id=release_id,
            name="Test",
            version="1.0.0",
            project_id=uuid4(),
            profile_id=profile_id,
            created_by=uuid4(),
            status=ReleaseStatus.EN_VERIFICACION,
            artifacts=[],
        )

        active_rule = VerificationRule(
            profile_id=profile_id,
            rule_template="active_rule",
            severity=SeverityType.HIGH,
            is_active=True,
        )
        inactive_rule = VerificationRule(
            profile_id=profile_id,
            rule_template="inactive_rule",
            severity=SeverityType.MEDIUM,
            is_active=False,
        )
        profile = VerificationProfile(
            id=profile_id,
            organization_id=uuid4(),
            name="Test Profile",
            description="",
            rules=[active_rule, inactive_rule],
        )

        with patch(
            "infrastructure.workers.verification_worker.SqlReleaseRepository"
        ) as mock_release_repo_class:
            with patch(
                "infrastructure.workers.verification_worker.SqlProfileRepository"
            ) as mock_profile_repo_class:
                with patch(
                    "infrastructure.workers.verification_worker.SqlVerificationResultRepository"
                ) as mock_ver_repo_class:
                    with patch(
                        "infrastructure.workers.verification_worker.create_registered_connector_registry"
                    ) as mock_registry_fn:
                        with patch(
                            "infrastructure.workers.verification_worker._call_verification_engine"
                        ) as mock_engine:
                            mock_release_repo = AsyncMock()
                            mock_release_repo.get_by_id = AsyncMock(return_value=release)
                            mock_release_repo.update_status = AsyncMock()
                            mock_release_repo_class.return_value = mock_release_repo

                            mock_profile_repo = AsyncMock()
                            mock_profile_repo.get_by_id = AsyncMock(return_value=profile)
                            mock_profile_repo_class.return_value = mock_profile_repo

                            saved_result = MagicMock()
                            saved_result.id = uuid4()
                            saved_result.verdict = VerdictType.VALID
                            saved_result.summary = ""

                            mock_ver_repo = AsyncMock()
                            mock_ver_repo.save = AsyncMock(return_value=saved_result)
                            mock_ver_repo_class.return_value = mock_ver_repo

                            mock_registry_fn.return_value = MagicMock()
                            mock_engine.return_value = {
                                "verdict": "VALID",
                                "rule_results": [],
                                "summary": "",
                            }

                            await _run_verification_async(release_id, task_id)

                            call_args = mock_engine.call_args
                            rules_sent = call_args[0][1]
                            assert len(rules_sent) == 1
                            assert rules_sent[0]["id"] == "active_rule"

    @pytest.mark.asyncio
    async def test_fetch_artifact_exception_swallowed(self):
        """Verifica que los errores al obtener artefactos se traguen."""
        release_id = uuid4()
        profile_id = uuid4()
        task_id = "task-123"

        release = Release(
            id=release_id,
            name="Test",
            version="1.0.0",
            project_id=uuid4(),
            profile_id=profile_id,
            created_by=uuid4(),
            status=ReleaseStatus.EN_VERIFICACION,
        )
        artifact = Artifact(
            id=uuid4(),
            release_id=release_id,
            connector_instance_id=uuid4(),
            connector_implementation="BROKEN",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        release.artifacts = [artifact]

        rule = VerificationRule(
            profile_id=profile_id,
            rule_template="check_1",
            severity=SeverityType.HIGH,
            is_active=True,
        )
        profile = VerificationProfile(
            id=profile_id,
            organization_id=uuid4(),
            name="Test",
            description="",
            rules=[rule],
        )

        with patch(
            "infrastructure.workers.verification_worker.SqlReleaseRepository"
        ) as mock_release_repo_class:
            with patch(
                "infrastructure.workers.verification_worker.SqlProfileRepository"
            ) as mock_profile_repo_class:
                with patch(
                    "infrastructure.workers.verification_worker.SqlVerificationResultRepository"
                ) as mock_ver_repo_class:
                    with patch(
                        "infrastructure.workers.verification_worker.create_registered_connector_registry"
                    ) as mock_registry_fn:
                        with patch(
                            "infrastructure.workers.verification_worker._call_verification_engine"
                        ) as mock_engine:
                            mock_release_repo = AsyncMock()
                            mock_release_repo.get_by_id = AsyncMock(return_value=release)
                            mock_release_repo.update_status = AsyncMock()
                            mock_release_repo_class.return_value = mock_release_repo

                            mock_profile_repo = AsyncMock()
                            mock_profile_repo.get_by_id = AsyncMock(return_value=profile)
                            mock_profile_repo_class.return_value = mock_profile_repo

                            # Simulate connector that throws
                            mock_connector = AsyncMock()
                            mock_connector.fetch_artifact = AsyncMock(side_effect=Exception("Boom"))
                            mock_registry = MagicMock()
                            mock_registry.get_by_implementation = MagicMock(return_value=mock_connector)
                            mock_registry_fn.return_value = mock_registry

                            saved_result = MagicMock()
                            saved_result.id = uuid4()
                            saved_result.verdict = VerdictType.VALID
                            saved_result.summary = ""

                            mock_ver_repo = AsyncMock()
                            mock_ver_repo.save = AsyncMock(return_value=saved_result)
                            mock_ver_repo_class.return_value = mock_ver_repo

                            mock_engine.return_value = {
                                "verdict": "VALID",
                                "rule_results": [],
                                "summary": "",
                            }

                            result = await _run_verification_async(release_id, task_id)

                            # Should not crash; artifacts_data should be empty since exception was swallowed
                            assert result["verdict"] == "VALID"
