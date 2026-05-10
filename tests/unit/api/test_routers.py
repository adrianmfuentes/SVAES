"""
Tests for API router handler functions.

Calls handler functions directly (bypassing FastAPI DI) to verify route logic,
status codes, and exception mapping without requiring an HTTP client.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from api.routers.auth import login
from api.routers.organizations import create_org, list_orgs
from api.routers.projects import create_project
from api.routers.profiles import create_profile
from api.routers.releases import create_release, get_results, verify_release, ReleaseCreate
from api.routers.connectors import create_connector
from api.schemas.auth import LoginRequest
from api.schemas.organization import OrganizationCreate
from api.schemas.project import ProjectCreate
from api.schemas.profile import ProfileCreate
from api.schemas.connector import ConnectorCreateRequest
from domain.entities.user import User
from domain.entities.organization import Organization
from domain.entities.project import Project
from domain.entities.release import Release
from domain.entities.enums import UserRole
from domain.exceptions import (
    EntityNotFoundError,
    ReleaseInvalidStateError,
    ConnectorConnectionFailedError,
)


@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        email="user@test.com",
        hashed_password="hashed",  # NOSONAR
        role=UserRole.OPERATOR,
        organization_id=uuid.uuid4(),
    )


@pytest.fixture
def fake_request():
    """Minimal mock of FastAPI Request, required by slowapi-decorated endpoints."""
    return MagicMock()


def _make_release():
    return Release(
        project_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        version="1.0.0",
        created_by=uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# Auth router
# ---------------------------------------------------------------------------

class TestAuthRouter:
    async def test_login_success_returns_token(self, fake_request):
        use_case = AsyncMock()
        use_case.execute.return_value = "jwt_token_abc"

        response = await login(
            request=fake_request,
            body=LoginRequest(email="user@test.com", password="pass"),  # NOSONAR
            use_case=use_case,
        )

        assert response.access_token == "jwt_token_abc"
        assert response.token_type == "bearer"

    async def test_login_value_error_raises_401(self, fake_request):
        use_case = AsyncMock()
        use_case.execute.side_effect = ValueError("credenciales inválidas")

        with pytest.raises(HTTPException) as exc_info:
            await login(
                request=fake_request,
                body=LoginRequest(email="x@x.com", password="wrong"),  # NOSONAR
                use_case=use_case,
            )

        assert exc_info.value.status_code == 401

    async def test_login_unexpected_exception_propagates(self, fake_request):
        """RuntimeError is NOT caught — it should propagate (becomes HTTP 500 via FastAPI)."""
        use_case = AsyncMock()
        use_case.execute.side_effect = RuntimeError("unexpected")

        with pytest.raises(RuntimeError):
            await login(
                request=fake_request,
                body=LoginRequest(email="x@x.com", password="pass"),  # NOSONAR
                use_case=use_case,
            )


# ---------------------------------------------------------------------------
# Organizations router
# ---------------------------------------------------------------------------

class TestOrganizationsRouter:
    async def test_create_org_returns_organization(self, mock_user):
        org = Organization(name="Acme", slug="acme")
        use_case = AsyncMock()
        use_case.execute.return_value = org

        result = await create_org(
            request=OrganizationCreate(name="Acme", slug="acme"),
            use_case=use_case,
            _current_user=mock_user,
        )

        assert result is org
        use_case.execute.assert_called_once()

    async def test_create_org_passes_plan(self, mock_user):
        org = Organization(name="Beta", slug="beta")
        use_case = AsyncMock()
        use_case.execute.return_value = org

        await create_org(
            request=OrganizationCreate(name="Beta", slug="beta", plan="pro"),
            use_case=use_case,
            _current_user=mock_user,
        )

        call_cmd = use_case.execute.call_args[0][0]
        assert call_cmd.plan == "pro"

    async def test_list_orgs_returns_list(self, mock_user):
        orgs = [Organization(name="A", slug="a"), Organization(name="B", slug="b")]
        use_case = AsyncMock()
        use_case.execute.return_value = orgs

        result = await list_orgs(use_case=use_case, _current_user=mock_user, skip=0, limit=50)

        assert result is orgs

    async def test_list_orgs_empty_list(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.return_value = []

        result = await list_orgs(use_case=use_case, _current_user=mock_user, skip=0, limit=50)

        assert result == []


# ---------------------------------------------------------------------------
# Projects router
# ---------------------------------------------------------------------------

class TestProjectsRouter:
    async def test_create_project_success(self, mock_user):
        project = Project(organization_id=uuid.uuid4(), name="Backend", description="")
        use_case = AsyncMock()
        use_case.execute.return_value = project

        result = await create_project(
            request=ProjectCreate(
                organization_id=project.organization_id,
                name="Backend",
                description="",
            ),
            use_case=use_case,
            _current_user=mock_user,
        )

        assert result is project

    async def test_create_project_passes_correct_command(self, mock_user):
        org_id = uuid.uuid4()
        project = Project(organization_id=org_id, name="API", description="Core service")
        use_case = AsyncMock()
        use_case.execute.return_value = project

        await create_project(
            request=ProjectCreate(
                organization_id=org_id,
                name="API",
                description="Core service",
            ),
            use_case=use_case,
            _current_user=mock_user,
        )

        cmd = use_case.execute.call_args[0][0]
        assert cmd.organization_id == org_id
        assert cmd.name == "API"
        assert cmd.description == "Core service"


# ---------------------------------------------------------------------------
# Profiles router
# ---------------------------------------------------------------------------

class TestProfilesRouter:
    async def test_create_profile_success(self, mock_user):
        from domain.entities.verification_profile import VerificationProfile
        profile = VerificationProfile(
            id=uuid.uuid4(), organization_id=uuid.uuid4(), name="Prod Checklist"
        )
        use_case = AsyncMock()
        use_case.create_profile.return_value = profile

        result = await create_profile(
            request=ProfileCreate(
                organization_id=profile.organization_id, name="Prod Checklist"
            ),
            use_case=use_case,
            _current_user=mock_user,
        )

        assert result is profile
        use_case.create_profile.assert_called_once()


# ---------------------------------------------------------------------------
# Releases router
# ---------------------------------------------------------------------------

class TestReleasesRouter:
    async def test_create_release_success(self, mock_user):
        release = _make_release()
        use_case = AsyncMock()
        use_case.execute.return_value = release

        result = await create_release(
            request=ReleaseCreate(
                project_id=release.project_id,
                profile_id=release.profile_id,
                version="1.0.0",
            ),
            use_case=use_case,
            current_user=mock_user,
        )

        assert result is release

    async def test_create_release_passes_creator(self, mock_user):
        release = _make_release()
        use_case = AsyncMock()
        use_case.execute.return_value = release

        await create_release(
            request=ReleaseCreate(
                project_id=release.project_id,
                profile_id=release.profile_id,
                version="2.0.0",
            ),
            use_case=use_case,
            current_user=mock_user,
        )

        cmd = use_case.execute.call_args[0][0]
        assert cmd.created_by == mock_user.id

    async def test_get_results_success(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.return_value = {"verdict": "PASSED", "duration_ms": 100}

        result = await get_results(
            release_id=uuid.uuid4(),
            use_case=use_case,
            _current_user=mock_user,
        )

        assert result["verdict"] == "PASSED"

    async def test_get_results_not_found_raises_404(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = EntityNotFoundError("release not found")

        with pytest.raises(HTTPException) as exc_info:
            await get_results(
                release_id=uuid.uuid4(),
                use_case=use_case,
                _current_user=mock_user,
            )

        assert exc_info.value.status_code == 404

    async def test_verify_release_success(self, mock_user):
        release = _make_release()
        use_case = AsyncMock()
        use_case.execute.return_value = (release, "task-abc-123")

        result = await verify_release(
            release_id=release.id,
            use_case=use_case,
            current_user=mock_user,
        )

        assert result.task_id == "task-abc-123"
        assert result.message == "Verification successfully queued"

    async def test_verify_release_not_found_raises_404(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = EntityNotFoundError("not found")

        with pytest.raises(HTTPException) as exc_info:
            await verify_release(
                release_id=uuid.uuid4(),
                use_case=use_case,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == 404

    async def test_verify_release_invalid_state_raises_409(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = ReleaseInvalidStateError(
            uuid.uuid4(), "BORRADOR", "PENDIENTE"
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_release(
                release_id=uuid.uuid4(),
                use_case=use_case,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == 409

    async def test_verify_release_runtime_error_raises_500(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = RuntimeError("queue unavailable")

        with pytest.raises(HTTPException) as exc_info:
            await verify_release(
                release_id=uuid.uuid4(),
                use_case=use_case,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == 500

    async def test_verify_release_value_error_raises_500(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = ValueError("bad state")

        with pytest.raises(HTTPException) as exc_info:
            await verify_release(
                release_id=uuid.uuid4(),
                use_case=use_case,
                current_user=mock_user,
            )

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Connectors router
# ---------------------------------------------------------------------------

class TestConnectorsRouter:
    async def test_create_connector_success(self, mock_user):
        connector = MagicMock()
        use_case = AsyncMock()
        use_case.execute.return_value = connector

        result = await create_connector(
            org_id=uuid.uuid4(),
            request=ConnectorCreateRequest(
                connector_type="github", name="GH CI", config_data={"token": "abc"}
            ),
            use_case=use_case,
            _current_user=mock_user,
        )

        assert result is connector

    async def test_create_connector_connection_failed_raises_400(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = ConnectorConnectionFailedError("bad credentials")

        with pytest.raises(HTTPException) as exc_info:
            await create_connector(
                org_id=uuid.uuid4(),
                request=ConnectorCreateRequest(
                    connector_type="github", name="GH", config_data={}
                ),
                use_case=use_case,
                _current_user=mock_user,
            )

        assert exc_info.value.status_code == 400

    async def test_create_connector_runtime_error_raises_500(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = RuntimeError("internal failure")

        with pytest.raises(HTTPException) as exc_info:
            await create_connector(
                org_id=uuid.uuid4(),
                request=ConnectorCreateRequest(
                    connector_type="github", name="GH", config_data={}
                ),
                use_case=use_case,
                _current_user=mock_user,
            )

        assert exc_info.value.status_code == 500

    async def test_create_connector_value_error_raises_500(self, mock_user):
        use_case = AsyncMock()
        use_case.execute.side_effect = ValueError("missing required field")

        with pytest.raises(HTTPException) as exc_info:
            await create_connector(
                org_id=uuid.uuid4(),
                request=ConnectorCreateRequest(
                    connector_type="github", name="GH", config_data={}
                ),
                use_case=use_case,
                _current_user=mock_user,
            )

        assert exc_info.value.status_code == 500
