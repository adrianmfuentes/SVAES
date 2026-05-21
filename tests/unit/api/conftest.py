import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "api"))

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_user_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_release_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.list_by_project = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_project_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_connector_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_organization_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_profile_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_artifact_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_verification_result_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_rule_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_custom_role_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_api_key_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_template_repository():
    repo = AsyncMock()
    repo._get_by_id = AsyncMock(return_value=None)
    repo._create = AsyncMock()
    repo._list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_notification_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_task_queue():
    queue = AsyncMock()
    queue.enqueue = AsyncMock()
    queue.get_status = AsyncMock(return_value="PENDING")
    return queue


@pytest.fixture
def mock_connector_registry():
    registry = MagicMock()
    registry.get = MagicMock(return_value=MagicMock())
    registry.list_all = MagicMock(return_value=[])
    return registry

@pytest.fixture
def test_user_id():
    return uuid4()

@pytest.fixture
def test_org_id():
    return uuid4()
