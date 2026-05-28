import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from application.use_cases.main.get_verification_history import GetVerificationHistoryUseCase
from domain.entities.verification_result import VerificationResult
from domain.enums import VerdictType
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def verification_repo():
    repo = AsyncMock()
    repo.find_by_release = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def use_case(verification_repo):
    return GetVerificationHistoryUseCase(verification_repo)


@pytest.fixture
def sample_results():
    return [
        VerificationResult(
            release_id=uuid4(),
            verdict=VerdictType.VALID,
            rule_results=[{"rule": "check_1", "status": "passed"}],
            summary={"total": 1, "passed": 1},
        ),
        VerificationResult(
            release_id=uuid4(),
            verdict=VerdictType.INVALID,
            rule_results=[{"rule": "check_2", "status": "failed"}],
            summary={"total": 1, "passed": 0},
        ),
    ]


class TestGetVerificationHistory:
    async def test_execute_returns_results(self, use_case, verification_repo, sample_results):
        """Verifica que se retorne el historial de verificaciones de una release."""
        release_id = uuid4()
        verification_repo.find_by_release.return_value = sample_results

        result = await use_case.execute(release_id)

        assert result == sample_results
        verification_repo.find_by_release.assert_called_once_with(release_id)

    async def test_execute_empty_history(self, use_case, verification_repo):
        """Verifica que se retorne una lista vacía cuando no hay resultados."""
        release_id = uuid4()
        verification_repo.find_by_release.return_value = []

        result = await use_case.execute(release_id)

        assert result == []

    async def test_execute_none_release_id_raises_error(self, use_case):
        """Verifica que se lance ValidationError cuando release_id es None."""
        with pytest.raises(ValidationError, match="release_id es requerido"):
            await use_case.execute(None)

    async def test_execute_falsy_release_id_raises_error(self, use_case):
        """Verifica que se lance ValidationError cuando release_id es vacío."""
        with pytest.raises(ValidationError, match="release_id es requerido"):
            await use_case.execute("")
