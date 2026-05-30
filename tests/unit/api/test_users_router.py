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
    get_user_service,
    get_jwt_handler,
)
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError, AuthenticationError
from domain.entities.user import User

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_user_service():
    svc = AsyncMock()
    svc.get_user_by_id = AsyncMock(return_value=None)
    svc.update_profile = AsyncMock()
    svc.change_password = AsyncMock(return_value=True)
    svc.delete_user_account = AsyncMock()
    svc.list_organization_users = AsyncMock(return_value=[])
    svc.invite_user = AsyncMock()
    svc.update_user_role = AsyncMock()
    svc.remove_user_from_organization = AsyncMock()
    svc.create_user = AsyncMock()
    svc.activate_user = AsyncMock()
    svc.deactivate_user = AsyncMock()
    svc.update_global_role = AsyncMock()
    svc.list_all_users = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def mock_token_service():
    svc = MagicMock()
    svc.blacklist_token = MagicMock()
    return svc


@pytest.fixture
def test_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U3,
        email="admin@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def test_app(mock_user_service, mock_token_service, test_user):
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_jwt_handler] = lambda: mock_token_service
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_permission(Permission.MANAGE_ROLES)] = lambda: test_user
    app.dependency_overrides[require_permission(Permission.INVITE_USERS)] = lambda: test_user
    app.dependency_overrides[require_role(UserRole.U3)] = lambda: test_user

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestGetCurrentUserProfile:
    def test_get_profile_success(self, test_app, mock_user_service, test_user):
        user = User(
            id=test_user.user_id,
            email="admin@test.com",
            hashed_password="hash",
            display_name="Admin",
            role=UserRole.U3,
            organization_ids=[test_user.organization_id],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.get_user_by_id.return_value = user

        response = test_app.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"

    def test_get_profile_not_found(self, test_app, mock_user_service):
        mock_user_service.get_user_by_id.return_value = None
        response = test_app.get("/api/v1/users/me")
        assert response.status_code == 404


class TestUpdateCurrentUserProfile:
    def test_update_profile_success(self, test_app, mock_user_service, test_user):
        user = User(
            id=test_user.user_id,
            email="admin@test.com",
            hashed_password="hash",
            display_name="Updated Name",
            role=UserRole.U3,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.update_profile.return_value = user

        response = test_app.patch("/api/v1/users/me", json={"display_name": "Updated Name"})
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    def test_update_profile_validation_error(self, test_app, mock_user_service):
        mock_user_service.update_profile.side_effect = ValidationError("Error")
        response = test_app.patch("/api/v1/users/me", json={"display_name": "Invalid"})
        assert response.status_code == 400


class TestChangePassword:
    def test_change_password_success(self, test_app, mock_user_service):
        response = test_app.post("/api/v1/users/me/password", json={
            "current_password": "old",
            "new_password": "newsecret123",
            "confirm_password": "newsecret123",
        })
        assert response.status_code == 200
        assert "cambiada" in response.json()["message"].lower()

    def test_change_password_wrong(self, test_app, mock_user_service):
        mock_user_service.change_password.return_value = False
        response = test_app.post("/api/v1/users/me/password", json={
            "current_password": "wrong",
            "new_password": "newsecret123",
            "confirm_password": "newsecret123",
        })
        assert response.status_code == 400


class TestExportUserData:
    def test_export_data_success(self, test_app, mock_user_service, test_user):
        user = User(
            id=test_user.user_id,
            email="admin@test.com",
            hashed_password="hash",
            display_name="Admin",
            role=UserRole.U3,
            organization_ids=[test_user.organization_id],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.get_user_by_id.return_value = user

        with patch("infrastructure.primary.routers.api.v1.users.get_audit_logger") as mock_audit:
            mock_logger = MagicMock()
            mock_logger.log = MagicMock()
            mock_audit.return_value = mock_logger

            response = test_app.get("/api/v1/users/me/export")
            assert response.status_code == 200
            assert "schema_version" in response.json()

    def test_export_data_not_found(self, test_app, mock_user_service):
        mock_user_service.get_user_by_id.return_value = None
        response = test_app.get("/api/v1/users/me/export")
        assert response.status_code == 404


class TestListOrganizationUsers:
    def test_list_users_success(self, test_app, mock_user_service):
        org_id = uuid4()
        response = test_app.get(f"/api/v1/organizations/{org_id}/users")
        assert response.status_code == 200


class TestInviteUser:
    def test_invite_user_success(self, test_app, mock_user_service, test_user):
        user = User(
            id=uuid4(),
            email="invited@test.com",
            hashed_password="hash",
            display_name="Invited",
            role=UserRole.U2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.invite_user.return_value = user

        response = test_app.post(f"/api/v1/organizations/{uuid4()}/users/invite", json={
            "email": "invited@test.com",
            "role": "OPERATOR",
        })
        assert response.status_code == 201

    def test_invite_user_duplicate(self, test_app, mock_user_service):
        mock_user_service.invite_user.side_effect = DuplicateEntityError("Ya existe")
        response = test_app.post(f"/api/v1/organizations/{uuid4()}/users/invite", json={
            "email": "exists@test.com",
            "role": "OPERATOR",
        })
        assert response.status_code == 409


class TestUpdateUserRole:
    def test_update_role_success(self, test_app, mock_user_service, test_user):
        user = User(
            id=uuid4(),
            email="user@test.com",
            hashed_password="hash",
            display_name="User",
            role=UserRole.U4,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.update_user_role.return_value = user

        response = test_app.patch(f"/api/v1/organizations/{uuid4()}/users/{uuid4()}/role", json={
            "role": "MANAGER",
        })
        assert response.status_code == 200

    def test_update_role_not_found(self, test_app, mock_user_service):
        mock_user_service.update_user_role.side_effect = EntityNotFoundError("No encontrado")
        response = test_app.patch(f"/api/v1/organizations/{uuid4()}/users/{uuid4()}/role", json={
            "role": "MANAGER",
        })
        assert response.status_code == 404

    def test_update_role_forbidden(self, test_app, mock_user_service):
        mock_user_service.update_user_role.side_effect = ValidationError("No permitido")
        response = test_app.patch(f"/api/v1/organizations/{uuid4()}/users/{uuid4()}/role", json={
            "role": "MANAGER",
        })
        assert response.status_code == 403


class TestRemoveUserFromOrg:
    def test_remove_user_success(self, test_app, mock_user_service):
        response = test_app.delete(f"/api/v1/organizations/{uuid4()}/users/{uuid4()}")
        assert response.status_code == 204

    def test_remove_user_not_found(self, test_app, mock_user_service):
        mock_user_service.remove_user_from_organization.side_effect = EntityNotFoundError("No encontrado")
        response = test_app.delete(f"/api/v1/organizations/{uuid4()}/users/{uuid4()}")
        assert response.status_code == 404


class TestAdminCreateUser:
    def test_admin_create_user_success(self, test_app, mock_user_service):
        user = User(
            id=uuid4(),
            email="new@test.com",
            hashed_password="hash",
            display_name="New User",
            role=UserRole.U2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.create_user.return_value = user

        response = test_app.post("/api/v1/admin/users", json={
            "email": "new@test.com",
            "display_name": "New User",
            "password": "password123",
            "role": "OPERATOR",
        })
        assert response.status_code == 201

    def test_admin_create_user_duplicate(self, test_app, mock_user_service):
        mock_user_service.create_user.side_effect = DuplicateEntityError("Ya existe")
        response = test_app.post("/api/v1/admin/users", json={
            "email": "exists@test.com",
            "display_name": "Exists",
            "password": "password123",
            "role": "OPERATOR",
        })
        assert response.status_code == 409


class TestAdminActivateUser:
    def test_activate_user_success(self, test_app, mock_user_service):
        user = User(
            id=uuid4(),
            email="user@test.com",
            hashed_password="hash",
            display_name="User",
            role=UserRole.U2,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.activate_user.return_value = user

        response = test_app.patch(f"/api/v1/admin/users/{uuid4()}/activate")
        assert response.status_code == 200

    def test_activate_user_not_found(self, test_app, mock_user_service):
        mock_user_service.activate_user.side_effect = EntityNotFoundError("No encontrado")
        response = test_app.patch(f"/api/v1/admin/users/{uuid4()}/activate")
        assert response.status_code == 404


class TestAdminDeactivateUser:
    def test_deactivate_user_success(self, test_app, mock_user_service):
        user = User(
            id=uuid4(),
            email="user@test.com",
            hashed_password="hash",
            display_name="User",
            role=UserRole.U2,
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.deactivate_user.return_value = user

        response = test_app.patch(f"/api/v1/admin/users/{uuid4()}/deactivate")
        assert response.status_code == 200

    def test_deactivate_user_forbidden(self, test_app, mock_user_service):
        mock_user_service.deactivate_user.side_effect = ValidationError("No permitido")
        response = test_app.patch(f"/api/v1/admin/users/{uuid4()}/deactivate")
        assert response.status_code == 403


class TestAdminUpdateGlobalRole:
    def test_update_global_role_success(self, test_app, mock_user_service):
        user = User(
            id=uuid4(),
            email="user@test.com",
            hashed_password="hash",
            display_name="User",
            role=UserRole.U3,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.update_global_role.return_value = user

        response = test_app.patch(f"/api/v1/admin/users/{uuid4()}/role", json={"role": "ADMIN"})
        assert response.status_code == 200

    def test_update_global_role_not_found(self, test_app, mock_user_service):
        mock_user_service.update_global_role.side_effect = EntityNotFoundError("No encontrado")
        response = test_app.patch(f"/api/v1/admin/users/{uuid4()}/role", json={"role": "ADMIN"})
        assert response.status_code == 404


class TestAdminListUsers:
    def test_admin_list_users_success(self, test_app, mock_user_service):
        user = User(
            id=uuid4(),
            email="user@test.com",
            hashed_password="hash",
            display_name="User",
            role=UserRole.U2,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_service.list_all_users.return_value = [user]

        response = test_app.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "user@test.com"
