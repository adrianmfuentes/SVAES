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
    get_template_service,
)
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError
from domain.entities.template import Template

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_template_service():
    svc = AsyncMock()
    svc.create_template = AsyncMock()
    svc.list_templates = AsyncMock(return_value=[])
    svc.get_template = AsyncMock(return_value=None)
    svc.update_template = AsyncMock()
    svc.archive_template = AsyncMock()
    svc.clone_template = AsyncMock()
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
def test_app(mock_template_service, test_user):
    app.dependency_overrides[get_template_service] = lambda: mock_template_service
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_permission(Permission.MANAGE_PROFILES)] = lambda: test_user

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestCreateTemplate:
    def test_create_template_success(self, test_app, mock_template_service):
        template = Template(
            id=uuid4(),
            organization_id=uuid4(),
            name="My Template",
            description="Test",
            profile_id=uuid4(),
            created_by=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_template_service.create_template.return_value = template

        response = test_app.post("/api/v1/templates", json={
            "name": "My Template",
            "description": "Test",
            "profile_id": str(uuid4()),
        })
        assert response.status_code == 201
        assert response.json()["name"] == "My Template"

    def test_create_template_validation_error(self, test_app, mock_template_service):
        mock_template_service.create_template.side_effect = ValidationError("Error de validacion")
        response = test_app.post("/api/v1/templates", json={
            "name": "Bad",
            "description": "Test",
            "profile_id": str(uuid4()),
        })
        assert response.status_code == 409


class TestListTemplates:
    def test_list_templates_success(self, test_app, mock_template_service):
        response = test_app.get("/api/v1/templates")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestGetTemplate:
    def test_get_template_success(self, test_app, mock_template_service):
        template = Template(
            id=uuid4(),
            organization_id=uuid4(),
            name="My Template",
            description="",
            profile_id=uuid4(),
            created_by=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_template_service.get_template.return_value = template

        response = test_app.get(f"/api/v1/templates/{uuid4()}")
        assert response.status_code == 200

    def test_get_template_not_found(self, test_app, mock_template_service):
        mock_template_service.get_template.return_value = None

        response = test_app.get(f"/api/v1/templates/{uuid4()}")
        assert response.status_code == 404


class TestUpdateTemplate:
    def test_update_template_success(self, test_app, mock_template_service):
        template = Template(
            id=uuid4(),
            organization_id=uuid4(),
            name="Updated",
            description="",
            profile_id=uuid4(),
            created_by=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_template_service.update_template.return_value = template

        response = test_app.patch(f"/api/v1/templates/{uuid4()}", json={
            "name": "Updated",
        })
        assert response.status_code == 200

    def test_update_template_not_found(self, test_app, mock_template_service):
        mock_template_service.update_template.side_effect = EntityNotFoundError("Template no encontrado")
        response = test_app.patch(f"/api/v1/templates/{uuid4()}", json={"name": "Nope"})
        assert response.status_code == 404


class TestArchiveTemplate:
    def test_archive_template_success(self, test_app, mock_template_service):
        response = test_app.post(f"/api/v1/templates/{uuid4()}/archive")
        assert response.status_code == 200

    def test_archive_template_not_found(self, test_app, mock_template_service):
        mock_template_service.archive_template.side_effect = EntityNotFoundError("Template no encontrado")
        response = test_app.post(f"/api/v1/templates/{uuid4()}/archive")
        assert response.status_code == 404


class TestCloneTemplate:
    def test_clone_template_success(self, test_app, mock_template_service):
        template = Template(
            id=uuid4(),
            organization_id=uuid4(),
            name="Cloned Template",
            description="",
            profile_id=uuid4(),
            created_by=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_template_service.clone_template.return_value = template

        response = test_app.post(f"/api/v1/templates/{uuid4()}/clone", json={
            "name": "Cloned Template",
            "target_organization_id": str(uuid4()),
        })
        assert response.status_code == 201

    def test_clone_template_not_found(self, test_app, mock_template_service):
        mock_template_service.clone_template.side_effect = EntityNotFoundError("Template no encontrado")
        response = test_app.post(f"/api/v1/templates/{uuid4()}/clone", json={
            "name": "Clone",
            "target_organization_id": str(uuid4()),
        })
        assert response.status_code == 404
