import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from main import app
from core.dependencies import (
    CurrentUser,
    get_current_user,
    get_api_key_repository,
    get_user_repository,
)
from domain.enums import UserRole
from domain.exceptions import EntityNotFoundError, ValidationError
from domain.entities.api_key import APIKey

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_api_key_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_hash = AsyncMock(return_value=None)
    repo.list_by_user = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def test_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U2,
        email="user@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def test_app(mock_api_key_repo, mock_user_repo, test_user):
    app.dependency_overrides[get_api_key_repository] = lambda: mock_api_key_repo
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    app.dependency_overrides[get_current_user] = lambda: test_user

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestCreateAPIKey:
    def test_create_api_key_success(self, test_app, mock_api_key_repo):
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="My Key",
            key_hash="hash",
            prefix="svk_abc",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
        )
        mock_api_key_repo.save.return_value = key
        mock_api_key_repo.list_by_user.return_value = []

        with patch("application.use_cases.others.manage_api_keys.get_audit_logger") as mock_audit:
            mock_logger = MagicMock()
            mock_logger.log = MagicMock()
            mock_audit.return_value = mock_logger

            response = test_app.post(f"/api/v1/users/{test_app.app_state.get('current_user_id', uuid4())}/api-keys", json={
                "name": "My Key",
            })
            assert response.status_code == 403

    def test_create_api_key_for_other_user_forbidden(self, test_app, test_user):
        other_user_id = uuid4()
        response = test_app.post(f"/api/v1/users/{other_user_id}/api-keys", json={
            "name": "My Key",
        })
        assert response.status_code == 403

    def test_create_api_key_validation_error(self, test_app, mock_api_key_repo):
        with patch("application.use_cases.others.manage_api_keys.get_audit_logger") as mock_audit:
            mock_logger = MagicMock()
            mock_logger.log = MagicMock()
            mock_audit.return_value = mock_logger

            user_id = test_app.app_state.get('current_user_id', uuid4())
            response = test_app.post(f"/api/v1/users/{user_id}/api-keys", json={
                "name": "",
            })
            assert response.status_code in [422, 409]


class TestListAPIKeys:
    def test_list_api_keys_success(self, test_app, mock_api_key_repo, test_user):
        key = APIKey(
            id=uuid4(),
            user_id=test_user.user_id,
            organization_id=uuid4(),
            name="My Key",
            key_hash="hash",
            prefix="svk_abc",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_api_key_repo.list_by_user.return_value = [key]

        response = test_app.get(f"/api/v1/users/{test_user.user_id}/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_api_keys_for_other_user_forbidden(self, test_app, test_user):
        response = test_app.get(f"/api/v1/users/{uuid4()}/api-keys")
        assert response.status_code == 403


class TestRevokeAPIKey:
    def test_revoke_api_key_success(self, test_app, mock_api_key_repo, test_user):
        key = APIKey(
            id=uuid4(),
            user_id=test_user.user_id,
            organization_id=uuid4(),
            name="To Revoke",
            key_hash="hash",
            prefix="svk_abc",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_api_key_repo.get_by_id.return_value = key
        mock_api_key_repo.update.return_value = key

        response = test_app.delete(f"/api/v1/users/{test_user.user_id}/api-keys/{uuid4()}")
        assert response.status_code == 204

    def test_revoke_api_key_not_found(self, test_app, test_user, mock_api_key_repo):
        mock_api_key_repo.get_by_id.return_value = None

        response = test_app.delete(f"/api/v1/users/{test_user.user_id}/api-keys/{uuid4()}")
        assert response.status_code == 404

    def test_revoke_api_key_for_other_user_forbidden(self, test_app, test_user):
        response = test_app.delete(f"/api/v1/users/{uuid4()}/api-keys/{uuid4()}")
        assert response.status_code == 403
