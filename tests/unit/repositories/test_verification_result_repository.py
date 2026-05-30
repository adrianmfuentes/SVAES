import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.verification_result import VerificationResult
from domain.enums import VerdictType

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "infrastructure.secondary.database.repositories.verification_result_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.verification_result_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.verification_result_repository.VerificationResultModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.verification_result_repository import (
                    SqlVerificationResultRepository,
                )
                yield SqlVerificationResultRepository()


class TestSave:
    async def test_save_result_success(self, repo, mock_session):
        result = VerificationResult(
            id=uuid4(),
            release_id=uuid4(),
            verdict=VerdictType.VALID,
            duration_ms=150,
            summary={"total_rules": 3, "passed": 3},
            rule_results=[{"rule": "check_status", "passed": True}],
            profile_snapshot={"profile": "default"},
            executed_at=datetime.now(timezone.utc),
        )
        saved = await repo.save(result)
        assert saved is not None
        assert saved.verdict == VerdictType.VALID
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestFindById:
    async def test_find_by_id_returns_result(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.release_id = uuid4()
        row.verdict = VerdictType.VALID_WITH_WARNINGS.value
        row.duration_ms = 200
        row.summary = {}
        row.rule_results = []
        row.profile_snapshot = {}
        row.executed_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        result = await repo.find_by_id(uuid4())
        assert result is not None
        assert result.verdict == VerdictType.VALID_WITH_WARNINGS

    async def test_find_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        result = await repo.find_by_id(uuid4())
        assert result is None


class TestFindByRelease:
    async def test_find_by_release_returns_results(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.release_id = uuid4()
        row.verdict = VerdictType.INVALID.value
        row.duration_ms = 300
        row.summary = {}
        row.rule_results = []
        row.profile_snapshot = {}
        row.executed_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        results = await repo.find_by_release(uuid4())
        assert len(results) == 1
        assert results[0].verdict == VerdictType.INVALID
