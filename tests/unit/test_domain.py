"""
Unit tests for domain layer: enums and exceptions.
"""

import os
import sys
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestSeverityConversion:
    """Cover severity_to_rule_severity and rule_severity_to_string branches."""

    def test_critical_severity_becomes_obligatoria(self):
        """Branch: severity is CRITICAL → RuleSeverityType.OBLIGATORIA"""
        from domain.enums import SeverityType, severity_to_rule_severity, RuleSeverityType
        assert severity_to_rule_severity(SeverityType.CRITICAL) == RuleSeverityType.OBLIGATORIA

    def test_high_severity_becomes_obligatoria(self):
        """Branch: severity is HIGH → RuleSeverityType.OBLIGATORIA"""
        from domain.enums import SeverityType, severity_to_rule_severity, RuleSeverityType
        assert severity_to_rule_severity(SeverityType.HIGH) == RuleSeverityType.OBLIGATORIA

    def test_medium_severity_becomes_opcional(self):
        """Branch: severity is MEDIUM → RuleSeverityType.OPCIONAL (else branch)"""
        from domain.enums import SeverityType, severity_to_rule_severity, RuleSeverityType
        assert severity_to_rule_severity(SeverityType.MEDIUM) == RuleSeverityType.OPCIONAL

    def test_low_severity_becomes_opcional(self):
        """Branch: severity is LOW → RuleSeverityType.OPCIONAL (else branch)"""
        from domain.enums import SeverityType, severity_to_rule_severity, RuleSeverityType
        assert severity_to_rule_severity(SeverityType.LOW) == RuleSeverityType.OPCIONAL

    def test_info_severity_becomes_opcional(self):
        """Branch: severity is INFO → RuleSeverityType.OPCIONAL (else branch)"""
        from domain.enums import SeverityType, severity_to_rule_severity, RuleSeverityType
        assert severity_to_rule_severity(SeverityType.INFO) == RuleSeverityType.OPCIONAL

    def test_rule_severity_to_string_returns_value(self):
        """Branch: rule_severity_to_string returns severity.value"""
        from domain.enums import RuleSeverityType, rule_severity_to_string
        assert rule_severity_to_string(RuleSeverityType.OBLIGATORIA) == "OBLIGATORIA"
        assert rule_severity_to_string(RuleSeverityType.OPCIONAL) == "OPCIONAL"
        assert rule_severity_to_string(RuleSeverityType.EXCLUIDA) == "EXCLUIDA"


class TestDomainExceptions:
    """Cover exception classes that have custom __init__."""

    def test_release_invalid_state_error_constructs_message(self):
        """Branch: ReleaseInvalidStateError.__init__ formats message with release/status args"""
        from domain.exceptions import ReleaseInvalidStateError, DomainException
        from uuid import uuid4
        from domain.enums import ReleaseStatus
        rid = uuid4()
        exc = ReleaseInvalidStateError(rid, ReleaseStatus.BORRADOR, ReleaseStatus.EN_VERIFICACION)
        assert str(rid) in str(exc)
        assert "BORRADOR" in str(exc)
        assert "EN_VERIFICACION" in str(exc)
        assert isinstance(exc, DomainException)

    def test_entity_not_found_error_inherits_domain_exception(self):
        """Branch: EntityNotFoundError inherits from DomainException"""
        from domain.exceptions import EntityNotFoundError, DomainException
        exc = EntityNotFoundError("test")
        assert exc.message == "test"
        assert isinstance(exc, DomainException)

    def test_duplicate_entity_error_inherits_domain_exception(self):
        """Branch: DuplicateEntityError stores message"""
        from domain.exceptions import DuplicateEntityError, DomainException
        exc = DuplicateEntityError("duplicate")
        assert isinstance(exc, DomainException)
        assert str(exc) == "duplicate"
