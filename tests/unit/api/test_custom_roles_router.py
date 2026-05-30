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
    require_permission,
    require_role,
    get_custom_role_service,
    get_custom_role_repository,
)
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError
from domain.entities.custom_role import CustomRole

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_custom_role_service():
    svc = AsyncMock()
    svc.list_roles = AsyncMock(return_value=[])
    svc.create_role = AsyncMock()
    svc.update_role = AsyncMock()
    svc.delete_role = AsyncMock()
    return svc


@pytest.fixture
def test_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U4,
        email="manager@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def test_app(mock_custom_role_service, test_user):
    mock_role_repo = AsyncMock()
    mock_role = MagicMock()
    mock_role.organization_id = test_user.organization_id
    mock_role_repo.get_by_id = AsyncMock(return_value=mock_role)

    app.dependency_overrides[get_custom_role_service] = lambda: mock_custom_role_service
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_permission(Permission.MANAGE_ROLES)] = lambda: test_user
    app.dependency_overrides[get_custom_role_repository] = lambda: mock_role_repo

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestListCustomRoles:
    def test_list_roles_success(self, test_app, mock_custom_role_service):
        role = CustomRole(
            id=uuid4(),
            organization_id=uuid4(),
            name="Reviewer",
            permissions=[Permission.VIEW_DASHBOARD],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_custom_role_service.list_roles.return_value = [role]

        response = test_app.get(f"/api/v1/organizations/{uuid4()}/roles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Reviewer"


class TestCreateCustomRole:
    def test_create_role_success(self, test_app, mock_custom_role_service):
        role = CustomRole(
            id=uuid4(),
            organization_id=uuid4(),
            name="New Role",
            permissions=[Permission.CREATE_RELEASE, Permission.EXECUTE_VERIFICATION],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_custom_role_service.create_role.return_value = role

        response = test_app.post(f"/api/v1/organizations/{uuid4()}/roles", json={
            "name": "New Role",
            "permissions": ["CREATE_RELEASE", "EXECUTE_VERIFICATION"],
        })
        assert response.status_code == 201
        assert response.json()["name"] == "New Role"

    def test_create_role_duplicate(self, test_app, mock_custom_role_service):
        mock_custom_role_service.create_role.side_effect = DuplicateEntityError("Ya existe")
        response = test_app.post(f"/api/v1/organizations/{uuid4()}/roles", json={
            "name": "Duplicate",
            "permissions": ["VIEW_DASHBOARD"],
        })
        assert response.status_code == 409

    def test_create_role_invalid_permission(self, test_app, mock_custom_role_service):
        mock_custom_role_service.create_role.side_effect = ValueError("Permiso invalido")
        response = test_app.post(f"/api/v1/organizations/{uuid4()}/roles", json={
            "name": "Bad Perm",
            "permissions": ["INVALID_PERM"],
        })
        assert response.status_code == 422


class TestUpdateCustomRole:
    def test_update_role_success(self, test_app, mock_custom_role_service):
        role = CustomRole(
            id=uuid4(),
            organization_id=uuid4(),
            name="Updated Role",
            permissions=[Permission.MANAGE_CONNECTORS],
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_custom_role_service.update_role.return_value = role

        response = test_app.patch(f"/api/v1/roles/{uuid4()}", json={
            "name": "Updated Role",
            "permissions": ["MANAGE_CONNECTORS"],
            "is_active": False,
        })
        assert response.status_code == 200

    def test_update_role_not_found(self, test_app, mock_custom_role_service):
        mock_custom_role_service.update_role.side_effect = EntityNotFoundError("Role no encontrado")
        response = test_app.patch(f"/api/v1/roles/{uuid4()}", json={"name": "Nope"})
        assert response.status_code == 404

    def test_update_role_duplicate(self, test_app, mock_custom_role_service):
        mock_custom_role_service.update_role.side_effect = DuplicateEntityError("Ya existe")
        response = test_app.patch(f"/api/v1/roles/{uuid4()}", json={"name": "Duplicate"})
        assert response.status_code == 409


class TestDeleteCustomRole:
    def test_delete_role_success(self, test_app, mock_custom_role_service):
        response = test_app.delete(f"/api/v1/roles/{uuid4()}")
        assert response.status_code == 204

    def test_delete_role_not_found(self, test_app, mock_custom_role_service):
        mock_custom_role_service.delete_role.side_effect = EntityNotFoundError("Role no encontrado")
        response = test_app.delete(f"/api/v1/roles/{uuid4()}")
        assert response.status_code == 404
