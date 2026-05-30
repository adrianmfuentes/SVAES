import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "infrastructure.secondary.database.repositories.rule_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.rule_repository.VerificationRuleModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.rule_repository import (
                    SqlVerificationRuleRepository,
                )
                yield SqlVerificationRuleRepository()


class TestCreate:
    async def test_create_rule_success(self, repo, mock_session):
        rule = VerificationRule(
            id=uuid4(),
            profile_id=uuid4(),
            rule_template="check_deployment_status",
            severity=SeverityType.HIGH,
            params={"required_status": "success"},
            connector_instance_id=uuid4(),
            display_order=1,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        result = await repo.create(rule)
        assert result is not None
        assert result.rule_template == "check_deployment_status"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_rule(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.profile_id = uuid4()
        row.rule_template = "check_approval"
        row.severity = SeverityType.CRITICAL.value
        row.params = {}
        row.connector_instance_id = None
        row.display_order = 0
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        rule = await repo.get_by_id(uuid4())
        assert rule is not None
        assert rule.rule_template == "check_approval"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        rule = await repo.get_by_id(uuid4())
        assert rule is None


class TestListAll:
    async def test_list_all_returns_rules(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.profile_id = uuid4()
        row.rule_template = "rule_1"
        row.severity = SeverityType.MEDIUM.value
        row.params = {}
        row.connector_instance_id = None
        row.display_order = 0
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        rules = await repo.list_all()
        assert len(rules) == 1


class TestListByProfile:
    async def test_list_by_profile_returns_rules(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.profile_id = uuid4()
        row.rule_template = "rule_1"
        row.severity = SeverityType.LOW.value
        row.params = {}
        row.connector_instance_id = None
        row.display_order = 0
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        rules = await repo.list_by_profile(uuid4())
        assert len(rules) == 1


class TestUpdate:
    async def test_update_rule_success(self, repo, mock_session):
        rule_id = uuid4()
        model = MagicMock()
        model.id = rule_id
        mock_session.get.return_value = model

        rule = VerificationRule(
            id=rule_id,
            profile_id=uuid4(),
            rule_template="updated_rule",
            severity=SeverityType.INFO,
            params={},
            display_order=2,
            is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        result = await repo.update(rule)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        rule = VerificationRule(
            id=uuid4(),
            profile_id=uuid4(),
            rule_template="nope",
            severity=SeverityType.HIGH,
            params={},
            created_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Rule not found"):
            await repo.update(rule)


class TestDelete:
    async def test_delete_rule_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Rule not found"):
            await repo.delete(uuid4())
