import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from application.use_cases.others.update_release import UpdateReleaseUseCase
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update = AsyncMock(side_effect=lambda r: r)
    return repo


@pytest.fixture
def use_case(release_repo):
    return UpdateReleaseUseCase(release_repo)


@pytest.fixture
def sample_release():
    release = MagicMock()
    release.id = uuid4()
    release.name = "old-name"
    release.version = "1.0.0"
    release.description = "old desc"
    return release


class TestUpdateReleaseSuccess:
    async def test_updates_all_fields(self, use_case, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release

        result = await use_case.execute(
            release_id=sample_release.id,
            name="v2.0.0",
            version="2.0.0",
            description="New description",
        )

        assert result.name == "v2.0.0"
        assert result.version == "2.0.0"
        assert result.description == "New description"
        release_repo.get_by_id.assert_called_once_with(sample_release.id)
        release_repo.update.assert_called_once_with(sample_release)

    async def test_updates_with_empty_description(self, use_case, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release

        result = await use_case.execute(
            release_id=sample_release.id,
            name="v3.0.0",
            version="3.0.0",
        )

        assert result.description == ""

    async def test_sets_fields_on_entity(self, use_case, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release

        await use_case.execute(
            release_id=sample_release.id,
            name="updated-name",
            version="5.5.5",
            description="updated-desc",
        )

        assert sample_release.name == "updated-name"
        assert sample_release.version == "5.5.5"
        assert sample_release.description == "updated-desc"


class TestUpdateReleaseInvalidSemver:
    @pytest.mark.parametrize("version", ["", "1", "v1.0.0", "01.0.0", "abc"])
    async def test_invalid_semver_raises(self, use_case, release_repo, sample_release, version):
        release_repo.get_by_id.return_value = sample_release

        with pytest.raises(ValidationError, match="SemVer"):
            await use_case.execute(
                release_id=sample_release.id,
                name="test",
                version=version,
            )

    async def test_invalid_semver_does_not_update(self, use_case, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release

        with pytest.raises(ValidationError):
            await use_case.execute(
                release_id=sample_release.id,
                name="test",
                version="bad-version",
            )

        release_repo.update.assert_not_called()


class TestUpdateReleaseNotFound:
    async def test_release_not_found_raises(self, use_case, release_repo):
        release_id = uuid4()
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="encontró"):
            await use_case.execute(
                release_id=release_id,
                name="test",
                version="1.0.0",
            )

    async def test_release_not_found_does_not_update(self, use_case, release_repo):
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError):
            await use_case.execute(
                release_id=uuid4(),
                name="test",
                version="1.0.0",
            )

        release_repo.update.assert_not_called()


class TestIsValidSemver:
    @pytest.mark.parametrize(
        "version",
        [
            "0.0.0", "1.0.0", "1.2.3", "10.20.30",
            "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
            "1.0.0-alpha-a.b-c-somethinglong", "1.0.0-0.3.7", "1.0.0-x.7.z.92",
            "1.0.0+build", "1.0.0+build.1", "1.0.0-alpha+build",
            "1.0.0-alpha.1+build.123", "1.0.0+build.123",
        ],
    )
    def test_valid_semver(self, use_case, version):
        assert use_case._is_valid_semver(version) is True

    @pytest.mark.parametrize(
        "version",
        [
            "", "1", "1.0", "v1.0.0", "01.0.0", "1.02.0", "1.0.03", "abc",
        ],
    )
    def test_invalid_semver(self, use_case, version):
        assert use_case._is_valid_semver(version) is False

    @pytest.mark.parametrize(
        "version,expected",
        [
            ("1.0.0+build.123", True),
            ("1.0.0-alpha", True),
            ("v2.0.0", False),
            ("not-valid", False),
        ],
    )
    def test_semver_tuple(self, use_case, version, expected):
        assert use_case._is_valid_semver(version) is expected
