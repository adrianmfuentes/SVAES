"""
Tests for the organizations router endpoints.

Uses dependency overrides to mock services and bypass auth checks.
"""
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
    get_organization_service,
)
from domain.entities.organization import Organization
from domain.entities.project import Project
from domain.enums import UserRole, Permission
from domain.exceptions import ValidationError, EntityNotFoundError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_org_service():
    svc = AsyncMock()
    svc.list_organizations = AsyncMock(return_value=[])
    svc.create_organization = AsyncMock()
    svc.get_organization = AsyncMock(return_value=None)
    svc.create_project = AsyncMock()
    svc.get_project = AsyncMock(return_value=None)
    svc.list_projects = AsyncMock(return_value=[])
    svc.list_accessible_projects = AsyncMock(return_value=[])
    svc.archive_project = AsyncMock()
    svc.restore_organization = AsyncMock()
    svc.transfer_ownership = AsyncMock()
    return svc


@pytest.fixture
def admin_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U3,
        email="admin@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def manager_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U4,
        email="manager@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def test_app(mock_org_service, admin_user):
    app.dependency_overrides[get_organization_service] = lambda: mock_org_service
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.VIEW_ORG_PROJECTS)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.CREATE_PROJECT)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.ARCHIVE_PROJECT)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.TRANSFER_OWNERSHIP)] = lambda: admin_user
    app.dependency_overrides[require_role(UserRole.U3)] = lambda: admin_user

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestListOrganizations:
    def test_list_organizations_success(self, test_app, mock_org_service):
        """Verifica que se listen las organizaciones correctamente."""
        org = Organization(
            id=uuid4(),
            name="Test Org",
            slug="test-org",
            owner_id=uuid4(),
            is_active=True,
            plan="default",
            created_at=datetime.now(timezone.utc),
        )
        mock_org_service.list_organizations.return_value = [org]

        response = test_app.get("/api/v1/organizations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_organizations_internal_error(self, test_app, mock_org_service):
        """Verifica que se retorne 500 en caso de error inesperado."""
        mock_org_service.list_organizations.side_effect = Exception("Boom")

        response = test_app.get("/api/v1/organizations")
        assert response.status_code == 500


class TestCreateOrganization:
    def test_create_organization_success(self, test_app, mock_org_service):
        """Verifica la creación exitosa de una organización."""
        org = Organization(
            id=uuid4(),
            name="New Org",
            slug="new-org",
            owner_id=uuid4(),
            is_active=True,
            plan="default",
        )
        mock_org_service.create_organization.return_value = org

        response = test_app.post(
            "/api/v1/organizations",
            json={"name": "New Org", "slug": "new-org", "plan": "default"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Org"
        assert "id" in data

    def test_create_organization_validation_error(self, test_app, mock_org_service):
        """Verifica que se retorne 409 ante error de validación."""
        mock_org_service.create_organization.side_effect = ValidationError("slug ya existe")

        response = test_app.post(
            "/api/v1/organizations",
            json={"name": "New Org", "slug": "existing-slug"},
        )
        assert response.status_code == 409

    def test_create_organization_internal_error(self, test_app, mock_org_service):
        """Verifica que se retorne 500 ante error inesperado."""
        mock_org_service.create_organization.side_effect = Exception("Boom")

        response = test_app.post(
            "/api/v1/organizations",
            json={"name": "New Org", "slug": "new-org"},
        )
        assert response.status_code == 500


class TestGetOrganization:
    def test_get_organization_success(self, test_app, mock_org_service, admin_user):
        """Verifica la obtención exitosa de una organización."""
        org_id = admin_user.organization_id
        org = Organization(
            id=org_id,
            name="My Org",
            slug="my-org",
            owner_id=admin_user.user_id,
            is_active=True,
            plan="default",
            created_at=datetime.now(timezone.utc),
        )
        mock_org_service.get_organization.return_value = org

        response = test_app.get(f"/api/v1/organizations/{org_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Org"

    def test_get_organization_not_found(self, test_app, mock_org_service):
        """Verifica que se retorne 404 cuando la organización no existe."""
        mock_org_service.get_organization.return_value = None

        response = test_app.get(f"/api/v1/organizations/{uuid4()}")
        assert response.status_code == 404

    def test_get_organization_internal_error(self, test_app, mock_org_service):
        """Verifica que se retorne 500 ante error inesperado."""
        mock_org_service.get_organization.side_effect = Exception("Boom")

        response = test_app.get(f"/api/v1/organizations/{uuid4()}")
        assert response.status_code == 500


class TestGetProjectById:
    def test_get_project_success(self, test_app, mock_org_service, admin_user):
        """Verifica la obtención exitosa de un proyecto por ID."""
        project = Project(
            id=uuid4(),
            name="Test Project",
            description="",
            organization_id=admin_user.organization_id,
            profile_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        mock_org_service.get_project.return_value = project

        response = test_app.get(f"/api/v1/projects/{project.id}")
        assert response.status_code == 200

    def test_get_project_not_found(self, test_app, mock_org_service):
        """Verifica que se retorne 404 cuando el proyecto no existe."""
        mock_org_service.get_project.return_value = None

        response = test_app.get(f"/api/v1/projects/{uuid4()}")
        assert response.status_code == 404


class TestListProjects:
    def test_list_projects_success(self, test_app, mock_org_service):
        """Verifica el listado de proyectos de una organización."""
        project = Project(
            id=uuid4(),
            name="Project",
            description="",
            organization_id=uuid4(),
            profile_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        mock_org_service.list_projects.return_value = [project]

        response = test_app.get(f"/api/v1/organizations/{uuid4()}/projects")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_projects_internal_error(self, test_app, mock_org_service):
        """Verifica que se retorne 500 ante error inesperado."""
        mock_org_service.list_projects.side_effect = Exception("Boom")

        response = test_app.get(f"/api/v1/organizations/{uuid4()}/projects")
        assert response.status_code == 500


class TestCreateProject:
    def test_create_project_success(self, test_app, mock_org_service):
        """Verifica la creación exitosa de un proyecto."""
        project = Project(
            id=uuid4(),
            name="New Project",
            description="",
            organization_id=uuid4(),
            profile_id=uuid4(),
        )
        mock_org_service.create_project.return_value = project

        response = test_app.post(
            f"/api/v1/organizations/{uuid4()}/projects",
            json={"name": "New Project", "description": "", "profile_id": str(project.profile_id)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"

    def test_create_project_not_found(self, test_app, mock_org_service):
        """Verifica que se retorne 404 cuando la organización no existe."""
        mock_org_service.create_project.side_effect = EntityNotFoundError("Organización no encontrada")

        response = test_app.post(
            f"/api/v1/organizations/{uuid4()}/projects",
            json={"name": "Project", "description": "", "profile_id": str(uuid4())},
        )
        assert response.status_code == 404

    def test_create_project_validation_error(self, test_app, mock_org_service):
        """Verifica que se retorne 409 ante error de validación."""
        mock_org_service.create_project.side_effect = ValidationError("Error de validación")

        response = test_app.post(
            f"/api/v1/organizations/{uuid4()}/projects",
            json={"name": "Project", "description": "", "profile_id": str(uuid4())},
        )
        assert response.status_code == 409


class TestArchiveProject:
    def test_archive_project_success(self, test_app, mock_org_service):
        """Verifica el archivado exitoso de un proyecto."""
        project = Project(
            id=uuid4(),
            name="Project",
            description="",
            organization_id=uuid4(),
            profile_id=uuid4(),
            is_archived=True,
        )
        mock_org_service.archive_project.return_value = project

        response = test_app.post(
            f"/api/v1/organizations/{uuid4()}/projects/{project.id}/archive",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True

    def test_archive_project_not_found(self, test_app, mock_org_service):
        """Verifica que se retorne 404 cuando el proyecto no existe."""
        mock_org_service.archive_project.side_effect = EntityNotFoundError("Proyecto no encontrado")

        response = test_app.post(
            f"/api/v1/organizations/{uuid4()}/projects/{uuid4()}/archive",
        )
        assert response.status_code == 404


class TestRestoreOrganization:
    def test_restore_organization_success(self, test_app, mock_org_service):
        """Verifica la restauración exitosa de una organización."""
        org = Organization(
            id=uuid4(),
            name="Restored Org",
            slug="restored-org",
            owner_id=uuid4(),
            is_active=True,
            plan="default",
        )
        mock_org_service.restore_organization.return_value = org

        response = test_app.post(f"/api/v1/organizations/{org.id}/restore")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_restore_organization_not_found(self, test_app, mock_org_service):
        """Verifica que se retorne 404 cuando la organización no existe."""
        mock_org_service.restore_organization.side_effect = EntityNotFoundError("Organización no encontrada")

        response = test_app.post(f"/api/v1/organizations/{uuid4()}/restore")
        assert response.status_code == 404

    def test_restore_organization_validation_error(self, test_app, mock_org_service):
        """Verifica que se retorne 409 cuando la organización ya está activa."""
        mock_org_service.restore_organization.side_effect = ValidationError("Organización ya está activa")

        response = test_app.post(f"/api/v1/organizations/{uuid4()}/restore")
        assert response.status_code == 409


class TestTransferOwnership:
    def test_transfer_ownership_success(self, test_app, mock_org_service):
        """Verifica la transferencia exitosa de propiedad."""
        new_owner_id = uuid4()
        org = Organization(
            id=uuid4(),
            name="Org",
            slug="org",
            owner_id=new_owner_id,
            is_active=True,
            plan="default",
        )
        mock_org_service.transfer_ownership.return_value = org

        response = test_app.post(
            f"/api/v1/organizations/{org.id}/transfer-ownership",
            json={"new_owner_id": str(new_owner_id)},
        )
        assert response.status_code == 200

    def test_transfer_ownership_not_found(self, test_app, mock_org_service):
        """Verifica que se retorne 404 cuando la organización no existe."""
        mock_org_service.transfer_ownership.side_effect = EntityNotFoundError("Organización no encontrada")

        response = test_app.post(
            f"/api/v1/organizations/{uuid4()}/transfer-ownership",
            json={"new_owner_id": str(uuid4())},
        )
        assert response.status_code == 404
