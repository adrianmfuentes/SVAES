"""
Tests for domain port interfaces (abstract base classes).

Creates minimal concrete subclasses and calls each abstract method through
super() to execute the default pass bodies and verify the interface contracts.
"""

import uuid
import pytest
from unittest.mock import MagicMock

from domain.ports.i_connector import IConnector
from domain.ports.i_verification_engine import IVerificationEngine
from domain.ports.i_user_repository import IUserRepository
from domain.ports.i_organization_repository import IOrganizationRepository
from domain.ports.i_project_repository import IProjectRepository
from domain.ports.i_release_repository import IReleaseRepository
from domain.ports.i_connector_repository import IConnectorRepository
from domain.ports.i_profile_repository import IProfileRepository
from domain.ports.i_artifact_repository import IArtifactRepository
from domain.ports.i_verification_result_repository import IVerificationResultRepository
from domain.ports.i_task_queue import ITaskQueue


# ---------------------------------------------------------------------------
# IConnector
# ---------------------------------------------------------------------------

class TestIConnector:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteConnector(IConnector):
            async def test_connection(self, config):
                return await super().test_connection(config)

            async def fetch_artifact(self, ref, config):
                return await super().fetch_artifact(ref, config)

            async def list_artifacts(self, filter_params, config):
                return await super().list_artifacts(filter_params, config)

            def get_metadata(self):
                return super().get_metadata()

        conn = ConcreteConnector()

        assert await conn.test_connection({}) is None
        assert await conn.fetch_artifact("sha:abc", {}) is None
        assert await conn.list_artifacts({}, {}) is None
        assert conn.get_metadata() is None

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            IConnector()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# IVerificationEngine
# ---------------------------------------------------------------------------

class TestIVerificationEngine:
    async def test_abstract_method_body_is_reachable(self):
        class ConcreteEngine(IVerificationEngine):
            async def execute_verification(self, release, profile, artifacts_data):
                return await super().execute_verification(release, profile, artifacts_data)

        engine = ConcreteEngine()
        result = await engine.execute_verification(MagicMock(), MagicMock(), [])

        assert result is None

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            IVerificationEngine()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# IUserRepository
# ---------------------------------------------------------------------------

class TestIUserRepository:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IUserRepository):
            async def create(self, user):
                return await super().create(user)

            async def get_by_id(self, user_id):
                return await super().get_by_id(user_id)

            async def get_by_email(self, email):
                return await super().get_by_email(email)

            async def list_all(self, active_only=True):
                return await super().list_all(active_only)

            async def update(self, user):
                return await super().update(user)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert await repo.create(stub) is None
        assert await repo.get_by_id(uuid.uuid4()) is None
        assert await repo.get_by_email("a@b.com") is None
        assert await repo.list_all() is None
        assert await repo.update(stub) is None


# ---------------------------------------------------------------------------
# IOrganizationRepository
# ---------------------------------------------------------------------------

class TestIOrganizationRepository:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IOrganizationRepository):
            async def create(self, organization):
                return await super().create(organization)

            async def get_by_id(self, organization_id):
                return await super().get_by_id(organization_id)

            async def get_by_slug(self, slug):
                return await super().get_by_slug(slug)

            async def list_all(self, active_only=True):
                return await super().list_all(active_only)

            async def update(self, organization):
                return await super().update(organization)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert await repo.create(stub) is None
        assert await repo.get_by_id(uuid.uuid4()) is None
        assert await repo.get_by_slug("acme") is None
        assert await repo.list_all() is None
        assert await repo.update(stub) is None


# ---------------------------------------------------------------------------
# IProjectRepository
# ---------------------------------------------------------------------------

class TestIProjectRepository:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IProjectRepository):
            async def create(self, project):
                return await super().create(project)

            async def get_by_id(self, project_id):
                return await super().get_by_id(project_id)

            async def list_by_organization(self, organization_id):
                return await super().list_by_organization(organization_id)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert await repo.create(stub) is None
        assert await repo.get_by_id(uuid.uuid4()) is None
        assert await repo.list_by_organization(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# IReleaseRepository
# ---------------------------------------------------------------------------

class TestIReleaseRepository:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IReleaseRepository):
            async def create(self, release):
                return await super().create(release)

            async def get_by_id(self, release_id):
                return await super().get_by_id(release_id)

            async def list_by_project(self, project_id):
                return await super().list_by_project(project_id)

            async def update(self, release):
                return await super().update(release)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert await repo.create(stub) is None
        assert await repo.get_by_id(uuid.uuid4()) is None
        assert await repo.list_by_project(uuid.uuid4()) is None
        assert await repo.update(stub) is None


# ---------------------------------------------------------------------------
# IConnectorRepository
# ---------------------------------------------------------------------------

class TestIConnectorRepository:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IConnectorRepository):
            async def save(self, connector):
                return await super().save(connector)

            async def get_by_id(self, instance_id):
                return await super().get_by_id(instance_id)

            async def list_by_organization(self, organization_id, active_only=True):
                return await super().list_by_organization(organization_id, active_only)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert await repo.save(stub) is None
        assert await repo.get_by_id(uuid.uuid4()) is None
        assert await repo.list_by_organization(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# IProfileRepository
# ---------------------------------------------------------------------------

class TestIProfileRepository:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IProfileRepository):
            async def create(self, profile):
                return await super().create(profile)

            async def get_by_id(self, profile_id):
                return await super().get_by_id(profile_id)

            async def get_default_for_organization(self, organization_id):
                return await super().get_default_for_organization(organization_id)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert await repo.create(stub) is None
        assert await repo.get_by_id(uuid.uuid4()) is None
        assert await repo.get_default_for_organization(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# IArtifactRepository (sync)
# ---------------------------------------------------------------------------

class TestIArtifactRepository:
    def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IArtifactRepository):
            def save(self, artifact):
                return super().save(artifact)

            def find_by_id(self, artifact_id):
                return super().find_by_id(artifact_id)

            def find_by_release(self, release_id):
                return super().find_by_release(release_id)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert repo.save(stub) is None
        assert repo.find_by_id(uuid.uuid4()) is None
        assert repo.find_by_release(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# IVerificationResultRepository (sync)
# ---------------------------------------------------------------------------

class TestIVerificationResultRepository:
    def test_abstract_method_bodies_are_reachable(self):
        class ConcreteRepo(IVerificationResultRepository):
            def save(self, result):
                return super().save(result)

            def find_by_id(self, result_id):
                return super().find_by_id(result_id)

            def find_by_release(self, release_id):
                return super().find_by_release(release_id)

        repo = ConcreteRepo()
        stub = MagicMock()

        assert repo.save(stub) is None
        assert repo.find_by_id(uuid.uuid4()) is None
        assert repo.find_by_release(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# ITaskQueue
# ---------------------------------------------------------------------------

class TestITaskQueue:
    async def test_abstract_method_bodies_are_reachable(self):
        class ConcreteQueue(ITaskQueue):
            async def enqueue_verification_task(self, release_id):
                return await super().enqueue_verification_task(release_id)

            async def get_task_status(self, task_id):
                return await super().get_task_status(task_id)

        queue = ConcreteQueue()

        assert await queue.enqueue_verification_task(uuid.uuid4()) is None
        assert await queue.get_task_status("task-abc") is None
