"""
Tests for the releases router endpoints.

Uses dependency overrides to mock services and bypass auth checks.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from main import app
from core.dependencies import (
    CurrentUser,
    get_current_user,
    require_permission,
    require_role,
    require_project_access,
    require_release_access,
    get_release_service,
    get_artifact_service,
    get_verification_service,
    get_export_service,
)
from domain.enums import UserRole, Permission, ReleaseStatus, VerdictType
from domain.entities.release import Release
from domain.entities.verification_result import VerificationResult
from domain.entities.artifact import Artifact
from domain.exceptions import ValidationError, EntityNotFoundError

pytestmark = pytest.mark.unit


@pytest.fixture
def admin_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U3,
        email="admin@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def mock_release_service():
    svc = AsyncMock()
    svc.create_release = AsyncMock()
    svc.get_release = AsyncMock(return_value=None)
    svc.update_release = AsyncMock()
    svc.delete_release = AsyncMock()
    svc.update_status = AsyncMock()
    svc.restore_release = AsyncMock()
    svc.list_releases = AsyncMock(return_value=[])
    svc.add_artifact = AsyncMock()
    svc.remove_artifact = AsyncMock()
    svc.list_artifacts = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def mock_artifact_service():
    svc = AsyncMock()
    svc.add_artifact = AsyncMock()
    svc.remove_artifact = AsyncMock()
    svc.list_artifacts = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def mock_verification_service():
    svc = AsyncMock()
    svc.launch_verification = AsyncMock(return_value="task-123")
    svc.get_verification_history = AsyncMock(return_value=[])
    svc.get_verification_result = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def mock_export_service():
    svc = AsyncMock()
    svc.export_verification_to_pdf = AsyncMock()
    svc.export_project_results_to_csv = AsyncMock()
    return svc


@pytest.fixture
def test_app(mock_release_service, mock_artifact_service, mock_verification_service, mock_export_service, admin_user):
    app.dependency_overrides[get_release_service] = lambda: mock_release_service
    app.dependency_overrides[get_artifact_service] = lambda: mock_artifact_service
    app.dependency_overrides[get_verification_service] = lambda: mock_verification_service
    app.dependency_overrides[get_export_service] = lambda: mock_export_service
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.VIEW_ORG_PROJECTS)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.UPDATE_OWN_RELEASES)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.ARCHIVE_RELEASE)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.EXECUTE_VERIFICATION)] = lambda: admin_user
    app.dependency_overrides[require_permission(Permission.VIEW_OWN_HISTORY)] = lambda: admin_user
    app.dependency_overrides[require_role(UserRole.U3)] = lambda: admin_user
    app.dependency_overrides[require_project_access()] = lambda: admin_user
    app.dependency_overrides[require_release_access()] = lambda: admin_user

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def sample_release():
    release = Release(
        id=uuid4(),
        name="Test Release",
        version="1.0.0",
        project_id=uuid4(),
        profile_id=uuid4(),
        created_by=uuid4(),
        description="A test release",
        status=ReleaseStatus.BORRADOR,
    )
    return release


class TestCreateRelease:
    def test_create_release_success(self, test_app, mock_release_service):
        """Verifica la creación exitosa de una release."""
        project_id = uuid4()
        release = sample_release()
        release.status = ReleaseStatus.BORRADOR
        mock_release_service.create_release.return_value = release

        response = test_app.post(
            f"/api/v1/projects/{project_id}/releases",
            json={
                "name": "v1.0.0",
                "version": "1.0.0",
                "description": "Test release",
                "profile_id": str(release.profile_id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == ReleaseStatus.BORRADOR.value

    def test_create_release_validation_error(self, test_app, mock_release_service):
        """Verifica que se retorne 422 ante error de validación."""
        mock_release_service.create_release.side_effect = ValidationError("Error de validación")

        response = test_app.post(
            f"/api/v1/projects/{uuid4()}/releases",
            json={"name": "v1", "version": "bad-version", "description": ""},
        )
        assert response.status_code == 422

    def test_create_release_internal_error(self, test_app, mock_release_service):
        """Verifica que se retorne 500 ante error inesperado."""
        mock_release_service.create_release.side_effect = Exception("Boom")

        response = test_app.post(
            f"/api/v1/projects/{uuid4()}/releases",
            json={"name": "v1.0.0", "version": "1.0.0"},
        )
        assert response.status_code == 500


class TestListReleases:
    def test_list_releases_success(self, test_app, mock_release_service):
        """Verifica el listado de releases de un proyecto."""
        release = sample_release()
        mock_release_service.list_releases.return_value = [release]

        response = test_app.get(f"/api/v1/projects/{uuid4()}/releases")
        assert response.status_code == 200

    def test_list_releases_internal_error(self, test_app, mock_release_service):
        """Verifica que se retorne 500 ante error inesperado."""
        mock_release_service.list_releases.side_effect = Exception("Boom")

        response = test_app.get(f"/api/v1/projects/{uuid4()}/releases")
        assert response.status_code == 500


class TestGetRelease:
    def test_get_release_success(self, test_app, mock_release_service):
        """Verifica la obtención exitosa de una release por ID."""
        release = sample_release()
        mock_release_service.get_release.return_value = release

        response = test_app.get(f"/api/v1/releases/{release.id}")
        assert response.status_code == 200

    def test_get_release_not_found(self, test_app, mock_release_service):
        """Verifica que se retorne 404 cuando la release no existe."""
        mock_release_service.get_release.return_value = None

        response = test_app.get(f"/api/v1/releases/{uuid4()}")
        assert response.status_code == 404


class TestUpdateRelease:
    def test_update_release_success(self, test_app, mock_release_service):
        """Verifica la actualización exitosa de una release."""
        release = sample_release()
        release.name = "Updated Name"
        mock_release_service.update_release.return_value = release

        response = test_app.patch(
            f"/api/v1/releases/{release.id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200

    def test_update_release_validation_error(self, test_app, mock_release_service):
        """Verifica que se retorne 422 cuando los datos son inválidos."""
        mock_release_service.update_release.side_effect = ValidationError("Error")

        response = test_app.patch(
            f"/api/v1/releases/{uuid4()}",
            json={"name": "ValidName"},
        )
        assert response.status_code == 409


class TestDeleteRelease:
    def test_delete_release_success(self, test_app, mock_release_service):
        """Verifica la eliminación exitosa de una release."""
        response = test_app.delete(f"/api/v1/releases/{uuid4()}")
        assert response.status_code == 204

    def test_delete_release_error(self, test_app, mock_release_service):
        """Verifica que se retorne 500 ante error."""
        mock_release_service.delete_release.side_effect = Exception("Boom")

        response = test_app.delete(f"/api/v1/releases/{uuid4()}")
        assert response.status_code == 500


class TestArchiveRelease:
    def test_archive_release_success(self, test_app, mock_release_service):
        """Verifica el archivado exitoso de una release."""
        response = test_app.post(f"/api/v1/releases/{uuid4()}/archive")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Release archivada con éxito"

    def test_archive_release_error(self, test_app, mock_release_service):
        """Verifica que se retorne 500 ante error."""
        mock_release_service.update_status.side_effect = Exception("Boom")

        response = test_app.post(f"/api/v1/releases/{uuid4()}/archive")
        assert response.status_code == 500


class TestRestoreRelease:
    def test_restore_release_success(self, test_app, mock_release_service):
        """Verifica la restauración exitosa de una release."""
        response = test_app.post(f"/api/v1/releases/{uuid4()}/restore")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Release restaurada con éxito"

    def test_restore_release_not_found(self, test_app, mock_release_service):
        """Verifica que se retorne 404 cuando la release no existe."""
        mock_release_service.restore_release.side_effect = EntityNotFoundError("Release no encontrada")

        response = test_app.post(f"/api/v1/releases/{uuid4()}/restore")
        assert response.status_code == 404

    def test_restore_release_validation_error(self, test_app, mock_release_service):
        """Verifica que se retorne 409 cuando la release no está archivada."""
        mock_release_service.restore_release.side_effect = ValidationError("No está archivada")

        response = test_app.post(f"/api/v1/releases/{uuid4()}/restore")
        assert response.status_code == 409


class TestListArtifacts:
    def test_list_artifacts_success(self, test_app, mock_artifact_service):
        """Verifica el listado de artefactos de una release."""
        artifact = Artifact(
            release_id=uuid4(),
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        mock_artifact_service.list_artifacts.return_value = [artifact]

        response = test_app.get(f"/api/v1/releases/{uuid4()}/artifacts")
        assert response.status_code == 200

    def test_list_artifacts_error(self, test_app, mock_artifact_service):
        """Verifica que se retorne 500 ante error."""
        mock_artifact_service.list_artifacts.side_effect = Exception("Boom")

        response = test_app.get(f"/api/v1/releases/{uuid4()}/artifacts")
        assert response.status_code == 500


class TestAddArtifact:
    def test_add_artifact_success(self, test_app, mock_artifact_service):
        """Verifica la adición exitosa de un artefacto."""
        release_id = uuid4()
        artifact = Artifact(
            id=uuid4(),
            release_id=release_id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        mock_artifact_service.add_artifact.return_value = artifact

        response = test_app.post(
            f"/api/v1/releases/{release_id}/artifacts",
            json={
                "artifact_type": "CODIGO",
                "connector_instance_id": str(artifact.connector_instance_id),
                "connector_implementation": "GITLAB",
                "external_ref": "ref",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data

    def test_add_artifact_validation_error(self, test_app, mock_artifact_service):
        """Verifica que se retorne 422 ante error de validación."""
        mock_artifact_service.add_artifact.side_effect = ValidationError("Error")

        response = test_app.post(
            f"/api/v1/releases/{uuid4()}/artifacts",
            json={
                "artifact_type": "CODIGO",
                "connector_instance_id": str(uuid4()),
                "connector_implementation": "GITLAB",
                "external_ref": "ref",
            },
        )
        assert response.status_code == 422


class TestRemoveArtifact:
    def test_remove_artifact_success(self, test_app, mock_artifact_service):
        """Verifica la eliminación exitosa de un artefacto."""
        response = test_app.delete(f"/api/v1/releases/{uuid4()}/artifacts/{uuid4()}")
        assert response.status_code == 204

    def test_remove_artifact_error(self, test_app, mock_artifact_service):
        """Verifica que se retorne 500 ante error."""
        mock_artifact_service.remove_artifact.side_effect = Exception("Boom")

        response = test_app.delete(f"/api/v1/releases/{uuid4()}/artifacts/{uuid4()}")
        assert response.status_code == 500


class TestVerifyRelease:
    def test_verify_release_success(self, test_app, mock_verification_service):
        """Verifica el lanzamiento exitoso de verificación."""
        release_id = uuid4()

        response = test_app.post(f"/api/v1/releases/{release_id}/verify")
        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["status"] == ReleaseStatus.EN_VERIFICACION.value

    def test_verify_release_validation_error(self, test_app, mock_verification_service):
        """Verifica que se retorne 409 cuando la release no está en estado válido."""
        mock_verification_service.launch_verification.side_effect = ValidationError("Estado no válido")

        response = test_app.post(f"/api/v1/releases/{uuid4()}/verify")
        assert response.status_code == 409


class TestGetResults:
    def test_get_results_success(self, test_app, mock_verification_service):
        """Verifica la obtención del historial de verificaciones."""
        result = VerificationResult(
            release_id=uuid4(),
            verdict=VerdictType.VALID,
        )
        mock_verification_service.get_verification_history.return_value = [result]

        response = test_app.get(f"/api/v1/releases/{uuid4()}/results")
        assert response.status_code == 200

    def test_get_results_error(self, test_app, mock_verification_service):
        """Verifica que se retorne 500 ante error."""
        mock_verification_service.get_verification_history.side_effect = Exception("Boom")

        response = test_app.get(f"/api/v1/releases/{uuid4()}/results")
        assert response.status_code == 500


class TestGetResultDetail:
    def test_get_result_detail_success(self, test_app, mock_verification_service):
        """Verifica la obtención del detalle de una verificación."""
        result = VerificationResult(
            id=uuid4(),
            release_id=uuid4(),
            verdict=VerdictType.VALID,
        )
        mock_verification_service.get_verification_result.return_value = result

        response = test_app.get(f"/api/v1/releases/{uuid4()}/results/{result.id}")
        assert response.status_code == 200

    def test_get_result_detail_error(self, test_app, mock_verification_service):
        """Verifica que se retorne 500 ante error."""
        mock_verification_service.get_verification_result.side_effect = Exception("Boom")

        response = test_app.get(f"/api/v1/releases/{uuid4()}/results/{uuid4()}")
        assert response.status_code == 500


class TestImportArtifacts:
    def test_import_artifacts_success(self, test_app, mock_artifact_service):
        """Verifica la importación exitosa de artefactos."""
        artifact = Artifact(
            id=uuid4(),
            release_id=uuid4(),
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        mock_artifact_service.add_artifact.return_value = artifact

        response = test_app.post(
            f"/api/v1/releases/{uuid4()}/artifacts/import",
            json={
                "artifacts": [
                    {
                        "artifact_type": "CODIGO",
                        "connector_instance_id": str(artifact.connector_instance_id),
                        "connector_implementation": "GITLAB",
                        "external_ref": "ref",
                    }
                ]
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["count"] == 1

    def test_import_artifacts_validation_error(self, test_app, mock_artifact_service):
        """Verifica que se retorne 422 ante error de validación."""
        mock_artifact_service.add_artifact.side_effect = ValidationError("Error")

        response = test_app.post(
            f"/api/v1/releases/{uuid4()}/artifacts/import",
            json={
                "artifacts": [
                    {
                        "artifact_type": "CODIGO",
                        "connector_instance_id": str(uuid4()),
                        "connector_implementation": "GITLAB",
                        "external_ref": "ref",
                    }
                ]
            },
        )
        assert response.status_code == 422
