"""
Unit tests for infrastructure.workers.scheduler_worker
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


class TestIsDue:
    """Tests for _is_due helper."""

    def test_no_schedule_returns_false(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.schedule = None
        now = datetime.now(timezone.utc)
        assert _is_due(profile, now) is False

    def test_empty_schedule_returns_false(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.schedule = ""
        now = datetime.now(timezone.utc)
        assert _is_due(profile, now) is False

    def test_invalid_cron_returns_false(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.schedule = "invalid cron"
        profile.schedule_last_run_at = None
        profile.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert _is_due(profile, now) is False

    def test_due_profile_first_check(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.schedule = "*/1 * * * *"
        profile.schedule_last_run_at = None
        profile.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert _is_due(profile, now) is True

    def test_not_due_yet(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.schedule = "0 0 1 1 *"
        profile.schedule_last_run_at = None
        profile.created_at = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        assert _is_due(profile, now) is False

    def test_uses_last_run_at_when_set(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.schedule = "*/1 * * * *"
        profile.schedule_last_run_at = datetime.now(timezone.utc)
        profile.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert _is_due(profile, now) is False


class TestTriggerDueProfilesAsync:
    """Tests for _trigger_due_profiles_async."""

    @pytest.mark.asyncio
    async def test_no_profiles(self):
        with patch("infrastructure.workers.scheduler_worker.SqlProfileRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.list_scheduled = AsyncMock(return_value=[])
            mock_repo_cls.return_value = mock_repo

            from infrastructure.workers.scheduler_worker import _trigger_due_profiles_async
            result = await _trigger_due_profiles_async()
            assert result["profiles_checked"] == 0
            assert result["triggered"] == 0
            assert result["skipped"] == 0
            assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_all_profiles_not_due(self):
        from infrastructure.workers.scheduler_worker import _is_due

        profile = MagicMock()
        profile.id = "p1"
        profile.schedule = "0 0 1 1 *"
        profile.schedule_last_run_at = datetime.now(timezone.utc)
        profile.created_at = datetime.now(timezone.utc)

        with patch("infrastructure.workers.scheduler_worker.SqlProfileRepository") as mock_repo_cls, \
             patch("infrastructure.workers.scheduler_worker._is_due", return_value=False):
            mock_repo = AsyncMock()
            mock_repo.list_scheduled = AsyncMock(return_value=[profile])
            mock_repo_cls.return_value = mock_repo

            from infrastructure.workers.scheduler_worker import _trigger_due_profiles_async
            result = await _trigger_due_profiles_async()
            assert result["profiles_checked"] == 1
            assert result["triggered"] == 0

    @pytest.mark.asyncio
    async def test_due_profile_triggers_releases(self):
        profile = MagicMock()
        profile.id = "p1"
        profile.schedule = "*/1 * * * *"

        release = MagicMock()
        release.id = "r1"

        with patch("infrastructure.workers.scheduler_worker.SqlProfileRepository") as mock_prof_repo_cls, \
             patch("infrastructure.workers.scheduler_worker.SqlReleaseRepository") as mock_rel_repo_cls, \
             patch("infrastructure.workers.scheduler_worker._build_verification_service") as mock_build_vs, \
             patch("infrastructure.workers.scheduler_worker._is_due", return_value=True):

            mock_prof_repo = AsyncMock()
            mock_prof_repo.list_scheduled = AsyncMock(return_value=[profile])
            mock_prof_repo.update_schedule_last_run = AsyncMock()
            mock_prof_repo_cls.return_value = mock_prof_repo

            mock_rel_repo = AsyncMock()
            mock_rel_repo.list_by_profile = AsyncMock(return_value=[release])
            mock_rel_repo_cls.return_value = mock_rel_repo

            mock_vs = AsyncMock()
            mock_vs.launch_verification = AsyncMock()
            mock_build_vs.return_value = mock_vs

            from infrastructure.workers.scheduler_worker import _trigger_due_profiles_async
            result = await _trigger_due_profiles_async()
            assert result["profiles_checked"] == 1
            assert result["triggered"] == 1
            assert result["skipped"] == 0
            assert result["errors"] == 0
            mock_prof_repo.update_schedule_last_run.assert_called_once()
            mock_vs.launch_verification.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_error_counts_as_skipped(self):
        profile = MagicMock()
        profile.id = "p1"
        profile.schedule = "*/1 * * * *"

        release = MagicMock()
        release.id = "r1"

        from domain.exceptions import ValidationError

        with patch("infrastructure.workers.scheduler_worker.SqlProfileRepository") as mock_prof_repo_cls, \
             patch("infrastructure.workers.scheduler_worker.SqlReleaseRepository") as mock_rel_repo_cls, \
             patch("infrastructure.workers.scheduler_worker._build_verification_service") as mock_build_vs, \
             patch("infrastructure.workers.scheduler_worker._is_due", return_value=True):

            mock_prof_repo = AsyncMock()
            mock_prof_repo.list_scheduled = AsyncMock(return_value=[profile])
            mock_prof_repo.update_schedule_last_run = AsyncMock()
            mock_prof_repo_cls.return_value = mock_prof_repo

            mock_rel_repo = AsyncMock()
            mock_rel_repo.list_by_profile = AsyncMock(return_value=[release])
            mock_rel_repo_cls.return_value = mock_rel_repo

            mock_vs = AsyncMock()
            mock_vs.launch_verification = AsyncMock(side_effect=ValidationError("no artifacts"))
            mock_build_vs.return_value = mock_vs

            from infrastructure.workers.scheduler_worker import _trigger_due_profiles_async
            result = await _trigger_due_profiles_async()
            assert result["triggered"] == 0
            assert result["skipped"] == 1
            assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_unexpected_error_counts_as_error(self):
        profile = MagicMock()
        profile.id = "p1"
        profile.schedule = "*/1 * * * *"

        release = MagicMock()
        release.id = "r1"

        with patch("infrastructure.workers.scheduler_worker.SqlProfileRepository") as mock_prof_repo_cls, \
             patch("infrastructure.workers.scheduler_worker.SqlReleaseRepository") as mock_rel_repo_cls, \
             patch("infrastructure.workers.scheduler_worker._build_verification_service") as mock_build_vs, \
             patch("infrastructure.workers.scheduler_worker._is_due", return_value=True):

            mock_prof_repo = AsyncMock()
            mock_prof_repo.list_scheduled = AsyncMock(return_value=[profile])
            mock_prof_repo.update_schedule_last_run = AsyncMock()
            mock_prof_repo_cls.return_value = mock_prof_repo

            mock_rel_repo = AsyncMock()
            mock_rel_repo.list_by_profile = AsyncMock(return_value=[release])
            mock_rel_repo_cls.return_value = mock_rel_repo

            mock_vs = AsyncMock()
            mock_vs.launch_verification = AsyncMock(side_effect=RuntimeError("boom"))
            mock_build_vs.return_value = mock_vs

            from infrastructure.workers.scheduler_worker import _trigger_due_profiles_async
            result = await _trigger_due_profiles_async()
            assert result["triggered"] == 0
            assert result["skipped"] == 0
            assert result["errors"] == 1
