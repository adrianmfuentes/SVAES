import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.release import Release
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_result import VerificationResult
from domain.enums import ReleaseStatus, VerdictType

pytestmark = pytest.mark.unit


class TestIVerificationEngineInterface:
    def test_interface_can_be_implemented(self):
        """Verifica que IVerificationEngine se pueda implementar como ABC."""
        from application.ports.output.i_verification_engine import IVerificationEngine

        class FakeEngine(IVerificationEngine):
            async def execute_verification(self, release, profile, artifacts_data):
                return VerificationResult(
                    release_id=uuid4(),
                    verdict=VerdictType.VALID,
                )

            async def health_check(self):
                return True

        engine = FakeEngine()
        assert isinstance(engine, IVerificationEngine)

    async def test_implementation_methods_are_callable(self):
        """Verifica que los metodos abstractos sean invocables en una implementacion concreta."""
        from application.ports.output.i_verification_engine import IVerificationEngine

        release = Release(
            name="Test Release",
            project_id=uuid4(),
            profile_id=uuid4(),
            version="1.0.0",
            created_by=uuid4(),
        )
        profile = MagicMock(spec=VerificationProfile)
        result = VerificationResult(
            release_id=uuid4(),
            verdict=VerdictType.VALID,
        )

        class FakeEngine(IVerificationEngine):
            async def execute_verification(self, release, profile, artifacts_data):
                return result

            async def health_check(self):
                return True

        engine = FakeEngine()
        res = await engine.execute_verification(release, profile, [])
        assert res == result

        healthy = await engine.health_check()
        assert healthy is True

    def test_abstract_class_cannot_be_instantiated(self):
        """Verifica que IVerificationEngine no se pueda instanciar directamente."""
        from application.ports.output.i_verification_engine import IVerificationEngine

        with pytest.raises(TypeError):
            IVerificationEngine()  # type: ignore[abstract]
