import pytest
from unittest.mock import MagicMock
from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry

pytestmark = pytest.mark.unit


@pytest.fixture
def registry():
    return ConnectorRegistry()


@pytest.fixture
def sample_connector():
    connector = MagicMock()
    connector.get_connector_type.return_value = "TAREA"
    connector.get_connector_implementation.return_value = "JIRA"
    return connector


class TestRegister:
    def test_register_by_type(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        assert registry.get_by_type("TAREA") is sample_connector

    def test_register_by_implementation(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        assert registry.get_by_implementation("JIRA") is sample_connector

    def test_register_case_insensitive_type(self, registry, sample_connector):
        registry.register("tarea", sample_connector)
        assert registry.get_by_type("TAREA") is sample_connector
        assert registry.get_by_type("tarea") is sample_connector

    def test_register_overwrites_existing(self, registry, sample_connector):
        other = MagicMock()
        other.get_connector_type.return_value = "TAREA"
        other.get_connector_implementation.return_value = "JIRA"
        registry.register("TAREA", other)

        registry.register("TAREA", sample_connector)
        assert registry.get_by_type("TAREA") is sample_connector


class TestGetByImplementation:
    def test_get_existing(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        assert registry.get_by_implementation("JIRA") is sample_connector

    def test_get_nonexistent_raises_keyerror(self, registry):
        with pytest.raises(KeyError, match="no registrada"):
            registry.get_by_implementation("NONEXISTENT")

    def test_get_case_insensitive(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        assert registry.get_by_implementation("jira") is sample_connector


class TestGetByType:
    def test_get_existing(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        assert registry.get_by_type("TAREA") is sample_connector

    def test_get_nonexistent_returns_none(self, registry):
        assert registry.get_by_type("NONEXISTENT") is None

    def test_get_safe_returns_none_for_nonexistent(self, registry):
        assert registry.get_by_type_safe("NONEXISTENT") is None


class TestListByType:
    def test_list_empty(self, registry):
        assert registry.list_by_type("TAREA") == []

    def test_list_returns_single(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        assert registry.list_by_type("TAREA") == [sample_connector]


class TestListAllImplementations:
    def test_list_all_empty(self, registry):
        assert registry.list_all_implementations() == []

    def test_list_all_multiple(self, registry):
        jira = MagicMock()
        jira.get_connector_type.return_value = "TAREA"
        jira.get_connector_implementation.return_value = "JIRA"
        gitlab = MagicMock()
        gitlab.get_connector_type.return_value = "REPO_CODIGO"
        gitlab.get_connector_implementation.return_value = "GITLAB"
        registry.register("TAREA", jira)
        registry.register("REPO_CODIGO", gitlab)

        impls = registry.list_all_implementations()
        assert len(impls) == 2
        assert "JIRA" in impls
        assert "GITLAB" in impls

    def test_list_all_case_insensitive_keys(self, registry, sample_connector):
        registry.register("TAREA", sample_connector)
        impls = registry.list_all_implementations()
        assert impls == ["JIRA"]
