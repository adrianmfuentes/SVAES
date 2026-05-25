import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from application.use_cases.main.release_service import CreateReleaseUseCase
from domain.entities.release import Release
from domain.entities.artifact import Artifact
from domain.enums import ReleaseStatus
from domain.exceptions import ValidationError


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_by_project = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    repo.update_status = AsyncMock(return_value=None)
    repo.delete = AsyncMock()
    repo.get_artifact_by_id = AsyncMock(return_value=None)
    repo.delete_artifact = AsyncMock()
    return repo


@pytest.fixture
def project_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def profile_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def service(release_repo, project_repo, profile_repo, mock_audit_logger):
    with patch(
        "application.use_cases.main.release_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo)


@pytest.fixture
def sample_project(project_repo):
    project = MagicMock()
    project.id = uuid4()
    project.organization_id = uuid4()
    project.profile_id = None
    project_repo.get_by_id.return_value = project
    return project


@pytest.fixture
def sample_release(sample_project):
    return Release(
        name="v1.0.0",
        version="1.0.0",
        project_id=sample_project.id,
        profile_id=uuid4(),
        created_by=uuid4(),
        description="Test release",
        status=ReleaseStatus.BORRADOR,
    )

pytestmark = pytest.mark.unit

class TestCreateRelease:
    async def test_create_release_success(self, service, sample_project, release_repo):
        """Verifica la creación exitosa de un release con estado BORRADOR y datos correctos."""
        result = await service.create_release(
            name="v1.0.0",
            version="1.0.0",
            project_id=sample_project.id,
            user_id=uuid4(),
            description="Initial release",
        )

        assert result.name == "v1.0.0"
        assert result.version == "1.0.0"
        assert result.status == ReleaseStatus.BORRADOR
        assert result.project_id == sample_project.id
        release_repo.create.assert_called_once()

    async def test_create_release_invalid_semver(self, service, sample_project):
        """Verifica que se lance ValidationError al crear un release con versión no SemVer."""
        with pytest.raises(ValidationError, match="SemVer"):
            await service.create_release(
                name="v1",
                version="not-semver",
                project_id=sample_project.id,
                user_id=uuid4(),
            )

    async def test_create_release_project_not_found(self, service, project_repo):
        """Verifica que se lance ValidationError cuando el proyecto asociado no existe."""
        project_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="proyecto"):
            await service.create_release(
                name="v1.0.0",
                version="1.0.0",
                project_id=uuid4(),
                user_id=uuid4(),
            )

    async def test_create_release_with_explicit_profile(
        self, service, sample_project, profile_repo
    ):
        """Verifica que se asigne correctamente un perfil explícito al crear un release."""
        profile = MagicMock()
        profile.id = uuid4()
        profile_repo.get_by_id.return_value = profile

        result = await service.create_release(
            name="v1.0.0",
            version="1.0.0",
            project_id=sample_project.id,
            user_id=uuid4(),
            profile_id=profile.id,
        )

        assert result.profile_id == profile.id

    async def test_create_release_profile_not_found(
        self, service, sample_project, profile_repo
    ):
        """Verifica que se lance ValidationError cuando el perfil explícito no existe."""
        profile_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="perfil"):
            await service.create_release(
                name="v1.0.0",
                version="1.0.0",
                project_id=sample_project.id,
                user_id=uuid4(),
                profile_id=uuid4(),
            )

    async def test_create_release_falls_back_to_project_profile(
        self, service, sample_project, profile_repo
    ):
        """Verifica que se use el perfil del proyecto como fallback si no se especifica perfil."""
        project_profile_id = uuid4()
        sample_project.profile_id = project_profile_id
        profile = MagicMock()
        profile.id = project_profile_id
        profile_repo.get_by_id.return_value = profile

        result = await service.create_release(
            name="v1.0.0",
            version="1.0.0",
            project_id=sample_project.id,
            user_id=uuid4(),
        )

        assert result.profile_id == project_profile_id

    async def test_create_release_skips_profile_validation_when_both_none(
        self, service, sample_project, profile_repo
    ):
        """Verifica que se omita la validación de perfil cuando ni el proyecto ni el release especifican uno."""
        sample_project.profile_id = None

        result = await service.create_release(
            name="v1.0.0",
            version="1.0.0",
            project_id=sample_project.id,
            user_id=uuid4(),
        )

        assert result.profile_id is None
        profile_repo.get_by_id.assert_not_called()


class TestGetRelease:
    async def test_get_release_found(self, service, sample_release, release_repo):
        """Verifica que al buscar un release existente se retorne el objeto correcto."""
        release_repo.get_by_id.return_value = sample_release
        result = await service.get_release(sample_release.id)
        assert result == sample_release
        release_repo.get_by_id.assert_called_once_with(sample_release.id)

    async def test_get_release_not_found(self, service, release_repo):
        """Verifica que se retorne None cuando el release solicitado no existe."""
        release_id = uuid4()
        result = await service.get_release(release_id)
        assert result is None
        release_repo.get_by_id.assert_called_once_with(release_id)


class TestListReleases:
    async def test_list_releases_returns_items(self, service, sample_release, release_repo):
        """Verifica que se listen correctamente los releases de un proyecto cuando existen."""
        release_repo.list_by_project.return_value = [sample_release]
        project_id = sample_release.project_id
        result = await service.list_releases(project_id)
        assert len(result) == 1
        assert result[0] == sample_release
        release_repo.list_by_project.assert_called_once_with(project_id, 0, 50)

    async def test_list_releases_empty(self, service, release_repo):
        """Verifica que se retorne una lista vacía cuando el proyecto no tiene releases."""
        project_id = uuid4()
        result = await service.list_releases(project_id)
        assert result == []
        release_repo.list_by_project.assert_called_once_with(project_id, 0, 50)

    async def test_list_releases_with_pagination(self, service, release_repo):
        """Verifica que se respeten los parámetros skip y limit en la paginación de releases."""
        project_id = uuid4()
        await service.list_releases(project_id, skip=10, limit=5)
        release_repo.list_by_project.assert_called_once_with(project_id, 10, 5)


class TestUpdateRelease:
    async def test_update_release_all_fields(self, service, sample_release, release_repo):
        """Verifica la actualización exitosa de todos los campos de un release."""
        release_repo.get_by_id.return_value = sample_release
        result = await service.update_release(
            release_id=sample_release.id,
            name="v2.0.0",
            version="2.0.0",
            description="Updated release",
            status=ReleaseStatus.PENDIENTE,
        )
        assert result.name == "v2.0.0"
        assert result.version == "2.0.0"
        assert result.description == "Updated release"
        assert result.status == ReleaseStatus.PENDIENTE
        release_repo.update.assert_called_once_with(result)

    async def test_update_release_partial_name_only(self, service, sample_release, release_repo):
        """Verifica que solo se actualice el campo name sin modificar los demás."""
        release_repo.get_by_id.return_value = sample_release
        original_version = sample_release.version
        result = await service.update_release(
            release_id=sample_release.id, name="new-name"
        )
        assert result.name == "new-name"
        assert result.version == original_version
        release_repo.update.assert_called_once()

    async def test_update_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al intentar actualizar un release inexistente."""
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="actualizar"):
            await service.update_release(release_id=uuid4(), name="test")

    async def test_update_release_invalid_semver(self, service, sample_release, release_repo):
        """Verifica que se lance ValidationError al actualizar la versión con un valor no SemVer."""
        release_repo.get_by_id.return_value = sample_release
        with pytest.raises(ValidationError, match="SemVer"):
            await service.update_release(
                release_id=sample_release.id, version="bad-version"
            )


class TestUpdateStatus:
    async def test_update_status_success(self, service, sample_release, release_repo):
        """Verifica la actualización exitosa del estado de un release."""
        sample_release.status = ReleaseStatus.ARCHIVADA
        release_repo.update_status.return_value = sample_release

        result = await service.update_status(
            sample_release.id, ReleaseStatus.ARCHIVADA
        )

        assert result.status == ReleaseStatus.ARCHIVADA
        release_repo.update_status.assert_called_once_with(
            sample_release.id, ReleaseStatus.ARCHIVADA
        )

    async def test_update_status_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al cambiar el estado de un release inexistente."""
        release_repo.update_status.return_value = None
        with pytest.raises(ValidationError, match="estado"):
            await service.update_status(uuid4(), ReleaseStatus.ARCHIVADA)


class TestAddArtifact:
    async def test_add_artifact_success(self, service, sample_release, release_repo):
        """Verifica la adición exitosa de un artifact a un release y su persistencia."""
        release_repo.get_by_id.return_value = sample_release
        conn_instance_id = uuid4()

        artifact = await service.add_artifact(
            release_id=sample_release.id,
            connector_instance_id=conn_instance_id,
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="https://gitlab.com/repo/commit/abc",
        )

        assert artifact.release_id == sample_release.id
        assert artifact.connector_instance_id == conn_instance_id
        assert artifact.connector_implementation == "GITLAB"
        assert artifact.artifact_type == "CODIGO"
        assert artifact.external_ref == "https://gitlab.com/repo/commit/abc"
        assert artifact.metadata == {}
        assert len(sample_release.artifacts) == 1
        release_repo.update.assert_called_once_with(sample_release)

    async def test_add_artifact_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al agregar un artifact a un release inexistente."""
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="agregar el artifact"):
            await service.add_artifact(
                release_id=uuid4(),
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type="CODIGO",
                external_ref="ref",
            )

    async def test_add_artifact_with_metadata(self, service, sample_release, release_repo):
        """Verifica que los metadatos opcionales se guarden correctamente al agregar un artifact."""
        release_repo.get_by_id.return_value = sample_release
        metadata = {"description": "Test task", "priority": "high"}

        artifact = await service.add_artifact(
            release_id=sample_release.id,
            connector_instance_id=uuid4(),
            connector_implementation="JIRA",
            artifact_type="TAREA",
            external_ref="PROJ-123",
            metadata=metadata,
        )

        assert artifact.metadata == metadata


class TestRemoveArtifact:
    async def test_remove_artifact_success(self, service, sample_release, release_repo):
        """Verifica la eliminación exitosa de un artifact y la actualización del release."""
        artifact = Artifact(
            release_id=sample_release.id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        sample_release.artifacts = [artifact]
        release_repo.get_artifact_by_id.return_value = artifact
        release_repo.get_by_id.return_value = sample_release

        await service.remove_artifact(artifact.id)

        assert len(sample_release.artifacts) == 0
        release_repo.update.assert_called_once_with(sample_release)
        release_repo.delete_artifact.assert_called_once_with(artifact.id)

    async def test_remove_artifact_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al eliminar un artifact inexistente."""
        release_repo.get_artifact_by_id.return_value = None
        with pytest.raises(ValidationError, match="artifact para eliminar"):
            await service.remove_artifact(uuid4())

    async def test_remove_artifact_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError si el release asociado al artifact no existe."""
        artifact = MagicMock()
        artifact.id = uuid4()
        artifact.release_id = uuid4()
        release_repo.get_artifact_by_id.return_value = artifact
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="asociado al artifact"):
            await service.remove_artifact(artifact.id)

    async def test_remove_artifact_handles_dict_result(
        self, service, sample_release, release_repo
    ):
        """Verifica que se maneje correctamente cuando get_artifact_by_id retorna un dict en vez de un objeto."""
        artifact_id = uuid4()
        artifact_in_release = Artifact(
            id=artifact_id,
            release_id=sample_release.id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        sample_release.artifacts = [artifact_in_release]
        release_repo.get_artifact_by_id.return_value = {
            "id": artifact_id,
            "release_id": str(sample_release.id),
        }
        release_repo.get_by_id.return_value = sample_release

        await service.remove_artifact(artifact_id)

        assert len(sample_release.artifacts) == 0


class TestListArtifacts:
    async def test_list_artifacts_returns_items(
        self, service, sample_release, release_repo
    ):
        """Verifica que se listen correctamente los artifacts de un release cuando existen."""
        artifacts = [
            Artifact(
                release_id=sample_release.id,
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type="CODIGO",
                external_ref="ref1",
            ),
            Artifact(
                release_id=sample_release.id,
                connector_instance_id=uuid4(),
                connector_implementation="JIRA",
                artifact_type="TAREA",
                external_ref="ref2",
            ),
        ]
        sample_release.artifacts = artifacts
        release_repo.get_by_id.return_value = sample_release

        result = await service.list_artifacts(sample_release.id)

        assert len(result) == 2
        assert result == artifacts

    async def test_list_artifacts_empty(self, service, sample_release, release_repo):
        """Verifica que se retorne una lista vacía cuando el release no tiene artifacts."""
        sample_release.artifacts = []
        release_repo.get_by_id.return_value = sample_release
        result = await service.list_artifacts(sample_release.id)
        assert result == []

    async def test_list_artifacts_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al listar artifacts de un release inexistente."""
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="listar sus artifacts"):
            await service.list_artifacts(uuid4())

    async def test_list_artifacts_with_pagination(
        self, service, sample_release, release_repo
    ):
        """Verifica que se respeten los parámetros skip y limit en la paginación de artifacts."""
        artifacts = [
            Artifact(
                release_id=sample_release.id,
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type="CODIGO",
                external_ref=f"ref{i}",
            )
            for i in range(10)
        ]
        sample_release.artifacts = artifacts
        release_repo.get_by_id.return_value = sample_release

        result = await service.list_artifacts(sample_release.id, skip=2, limit=3)

        assert len(result) == 3
        assert result == artifacts[2:5]


class TestDeleteRelease:
    async def test_delete_release_success(self, service, sample_release, release_repo):
        """Verifica la eliminación exitosa de un release existente."""
        release_repo.get_by_id.return_value = sample_release
        await service.delete_release(sample_release.id)
        release_repo.delete.assert_called_once_with(sample_release.id)

    async def test_delete_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al eliminar un release inexistente."""
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="eliminar"):
            await service.delete_release(uuid4())


class TestRestoreRelease:
    async def test_restore_release_success(self, service, sample_release, release_repo):
        """Verifica la restauración exitosa de un release archivado al estado BORRADOR."""
        sample_release.status = ReleaseStatus.ARCHIVADA
        release_repo.get_by_id.return_value = sample_release

        await service.restore_release(sample_release.id)

        assert sample_release.status == ReleaseStatus.BORRADOR
        release_repo.update.assert_called_once_with(sample_release)

    async def test_restore_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError al restaurar un release inexistente."""
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="restaurar"):
            await service.restore_release(uuid4())

    async def test_restore_release_not_archived(self, service, sample_release, release_repo):
        """Verifica que se lance ValidationError al restaurar un release que no está archivado."""
        sample_release.status = ReleaseStatus.VALIDA
        release_repo.get_by_id.return_value = sample_release
        with pytest.raises(ValidationError, match="archivadas"):
            await service.restore_release(sample_release.id)


class TestSemverValidation:
    @pytest.mark.parametrize(
        "version",
        [
            "0.0.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-alpha-a.b-c-somethinglong",
            "1.0.0-0.3.7",
            "1.0.0-x.7.z.92",
            "1.0.0+build",
            "1.0.0+build.1",
            "1.0.0-alpha+build",
            "1.0.0-alpha.1+build.123",
        ],
    )
    def test_valid_semver(self, service, version):
        """Verifica que versiones SemVer válidas sean aceptadas correctamente."""
        assert service._is_valid_semver(version) is True

    @pytest.mark.parametrize(
        "version",
        [
            "",
            "1",
            "1.0",
            "v1.0.0",
            "01.0.0",
            "1.02.0",
            "1.0.03",
            "1.0.0-",
            "1.0.0+",
            "abc",
        ],
    )
    def test_invalid_semver(self, service, version):
        """Verifica que versiones no SemVer sean rechazadas correctamente."""
        assert service._is_valid_semver(version) is False
