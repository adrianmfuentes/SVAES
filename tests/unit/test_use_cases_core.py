"""Unit tests for credential encryption and verification result processing."""

import os
import sys
import pytest
from unittest.mock import MagicMock
from uuid import uuid4, UUID

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit

VALID_FERNET_KEY = "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=" # NOSONAR


# ── helpers ──────────────────────────────────────────────────────────────────

class TestFernetCredentialEncryptor:
    @pytest.fixture
    def encryptor(self):
        from shared.infrastructure.fernet_encryptor import FernetCredentialEncryptor
        return FernetCredentialEncryptor(VALID_FERNET_KEY)

    def test_init_with_string_key_encodes_to_bytes(self):
        """Branch: key is str → encoded to bytes before Fernet init"""
        from shared.infrastructure.fernet_encryptor import FernetCredentialEncryptor
        enc = FernetCredentialEncryptor(VALID_FERNET_KEY)
        assert enc._fernet is not None

    def test_init_with_bytes_key_uses_directly(self):
        """Branch: key is bytes → used directly without encoding"""
        from shared.infrastructure.fernet_encryptor import FernetCredentialEncryptor
        key_bytes = VALID_FERNET_KEY.encode()
        enc = FernetCredentialEncryptor(key_bytes)  # type: ignore[arg-type]
        assert enc._fernet is not None

    def test_encrypt_returns_bytes(self, encryptor):
        """Branch: encrypt returns bytes (Fernet token)"""
        result = encryptor.encrypt("hello world", uuid4())
        assert isinstance(result, bytes)
        assert result != b"hello world"

    def test_decrypt_returns_original_string(self, encryptor):
        """Branch: decrypt reverses encrypt"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt("secret data", instance_id)
        decrypted = encryptor.decrypt(encrypted, instance_id)
        assert decrypted == "secret data"

    def test_encrypt_bytes_returns_bytes(self, encryptor):
        """Branch: encrypt_bytes returns Fernet token from bytes input"""
        result = encryptor.encrypt_bytes(b"binary data", uuid4())
        assert isinstance(result, bytes)

    def test_decrypt_bytes_returns_original_bytes(self, encryptor):
        """Branch: decrypt_bytes reverses encrypt_bytes"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt_bytes(b"binary payload", instance_id)
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id)
        assert decrypted == b"binary payload"

    def test_decrypt_with_wrong_instance_id_still_works(self, encryptor):
        """Branch: decrypt ignores instance_id (Fernet does not use it)"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt("data", instance_id)
        decrypted = encryptor.decrypt(encrypted, uuid4())
        assert decrypted == "data"

    def test_decrypt_bytes_with_associated_data_ignored(self, encryptor):
        """Branch: associated_data is accepted but ignored (interface compliance)"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt_bytes(b"payload", instance_id, {"ctx": "test"})
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id, {"ctx": "other"})
        assert decrypted == b"payload"

    def test_encrypt_with_associated_data_provided_ignored(self, encryptor):
        """Branch: encrypt with optional associated_data parameter"""
        result = encryptor.encrypt("test", uuid4(), associated_data={"key": "value"})
        assert isinstance(result, bytes)


# ── 8. pseudonymize ──────────────────────────────────────────────────────────

class TestPseudonymize:
    def test_scalar_passthrough_int(self):
        """Branch: input is int → returned as-is"""
        from features.verification.application.pseudonymizer import pseudonymize
        assert pseudonymize(42) == 42

    def test_scalar_passthrough_string(self):
        """Branch: input is str → returned as-is"""
        from features.verification.application.pseudonymizer import pseudonymize
        assert pseudonymize("plain text") == "plain text"

    def test_scalar_passthrough_none(self):
        """Branch: input is None → returned as-is"""
        from features.verification.application.pseudonymizer import pseudonymize
        assert pseudonymize(None) is None

    def test_empty_dict_returns_empty_dict(self):
        """Branch: input is empty dict → returned empty dict"""
        from features.verification.application.pseudonymizer import pseudonymize
        assert pseudonymize({}) == {}

    def test_dict_non_pii_keys_passthrough(self):
        """Branch: dict with non-PII keys → values passed through"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"task_id": "T-123", "status": "open", "priority": "high"}
        result = pseudonymize(data)
        assert result == data

    def test_dict_pii_email_is_hashed(self):
        """Branch: dict key 'email' with non-empty str → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"email": "user@example.com"}
        result = pseudonymize(data)
        assert result["email"].startswith("sha256:")
        assert result["email"] != "user@example.com"

    def test_dict_pii_name_is_hashed(self):
        """Branch: dict key 'name' (PII) → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"name": "John Doe"}
        result = pseudonymize(data)
        assert result["name"].startswith("sha256:")

    def test_dict_pii_displayname_is_hashed(self):
        """Branch: dict key 'displayName' (case-insensitive PII) → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"displayName": "Jane"}
        result = pseudonymize(data)
        assert result["displayName"].startswith("sha256:")

    def test_dict_pii_username_is_hashed(self):
        """Branch: dict key 'username' (PII) → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"username": "jdoe"}
        result = pseudonymize(data)
        assert result["username"].startswith("sha256:")

    def test_dict_pii_assignee_is_hashed(self):
        """Branch: dict key 'assignee' (PII) → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"assignee": "worker@corp.com"}
        result = pseudonymize(data)
        assert result["assignee"].startswith("sha256:")

    def test_dict_pii_author_is_hashed(self):
        """Branch: dict key 'author' (PII) → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"author": "writer"}
        result = pseudonymize(data)
        assert result["author"].startswith("sha256:")

    def test_dict_pii_fullname_is_hashed(self):
        """Branch: dict key 'fullName' (case-insensitive PII) → hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"fullName": "Full Name Here"}
        result = pseudonymize(data)
        assert result["fullName"].startswith("sha256:")

    def test_dict_pii_empty_string_not_hashed(self):
        """Branch: PII key but value is empty str → not hashed (remains empty)"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"email": ""}
        result = pseudonymize(data)
        assert result["email"] == ""

    def test_dict_pii_non_string_value_not_hashed(self):
        """Branch: PII key but value is not str (e.g. list) → not hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"email": ["a", "b"]}
        result = pseudonymize(data)
        assert result["email"] == ["a", "b"]

    def test_list_of_dicts_each_processed(self):
        """Branch: input is list of dicts → each item pseudonymized"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = [{"email": "a@b.com"}, {"email": "c@d.com"}]
        result = pseudonymize(data)
        assert result[0]["email"].startswith("sha256:")
        assert result[1]["email"].startswith("sha256:")

    def test_nested_dict_pii_inner_hashed(self):
        """Branch: nested dict → inner PII keys hashed"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"ticket": {"author": "dev1", "title": "fix bug"}}
        result = pseudonymize(data)
        assert result["ticket"]["author"].startswith("sha256:")
        assert result["ticket"]["title"] == "fix bug"

    def test_list_inside_dict_processed(self):
        """Branch: dict value is a list → each item in list pseudonymized"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"comments": [{"author": "u1"}, {"author": "u2"}]}
        result = pseudonymize(data)
        assert result["comments"][0]["author"].startswith("sha256:")
        assert result["comments"][1]["author"].startswith("sha256:")

    def test_mixed_types_passthrough(self):
        """Branch: float and bool values passed through unchanged"""
        from features.verification.application.pseudonymizer import pseudonymize
        data = {"count": 5, "active": True, "rating": 4.5}
        result = pseudonymize(data)
        assert result == data

    def test_is_pii_key_case_insensitive(self):
        """Branch: _is_pii_key uses key.lower() → case insensitive"""
        from features.verification.application.pseudonymizer import _is_pii_key
        assert _is_pii_key("EMAIL") is True
        assert _is_pii_key("Email") is True
        assert _is_pii_key("eMaIl") is True
        assert _is_pii_key("task_id") is False

    def test_hash_value_returns_prefixed_sha256(self):
        """Branch: _hash_value returns 'sha256:' + hex digest"""
        from features.verification.application.pseudonymizer import _hash_value
        import hashlib
        value = "test@example.com"
        expected = "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
        assert _hash_value(value) == expected


# ── 9. _get_connector_for_rule ───────────────────────────────────────────────

class TestGetConnectorForRule:
    """Unit tests for rule_results._get_connector_for_rule."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from features.verification.application.rule_results import _get_connector_for_rule
        self.fn = _get_connector_for_rule

    def _make_rule(self, connector_instance_id=None, params=None):
        from features.verification.domain.verification_rule import VerificationRule
        return VerificationRule(
            profile_id=uuid4(),
            rule_template="RV-03",
            connector_instance_id=connector_instance_id,
            params=params or {},
        )

    def test_returns_name_when_connector_found(self):
        """Rule has connector_instance_id that exists in connector_names → returns name."""
        cid = uuid4()
        rule = self._make_rule(connector_instance_id=cid)
        connector_names = {cid: "Jira"}
        result = self.fn("RV-03", {}, {"RV-03": rule}, connector_names)
        assert result == "Jira"

    def test_falls_through_to_artifact_type_when_connector_missing(self):
        """Rule has connector_instance_id but it's not in connector_names →
        falls back to artifact_type_connector (the bug-fix case)."""
        cid = uuid4()
        rule = self._make_rule(connector_instance_id=cid)
        connector_names = {}  # connector deleted / not found
        artifact_type_connector = {"TAREA": "Jira"}
        result = self.fn("RV-03", {}, {"RV-03": rule}, connector_names, artifact_type_connector)
        assert result == "Jira"

    def test_returns_empty_when_no_connector_and_no_artifact_type(self):
        """Rule has no connector_instance_id and rule not in RULE_DEFAULT_ARTIFACT_TYPES."""
        rule = self._make_rule()
        result = self.fn("RV-01", {}, {"RV-01": rule}, {}, {})
        assert result == ""

    def test_uses_artifact_type_fallback_when_no_connector_instance(self):
        """Rule with no connector_instance_id uses RULE_DEFAULT_ARTIFACT_TYPES fallback."""
        rule = self._make_rule()
        artifact_type_connector = {"TAREA": "Taiga"}
        result = self.fn("RV-03", {}, {"RV-03": rule}, {}, artifact_type_connector)
        assert result == "Taiga"

    def test_artifact_fetch_error_uses_connector_instance_id_from_result(self):
        """artifact_fetch_error entries use connector_instance_id from the rule_result dict."""
        cid = uuid4()
        connector_names = {cid: "Sonar"}
        rule_result = {"connector_instance_id": str(cid)}
        result = self.fn("artifact_fetch_error", rule_result, {}, connector_names)
        assert result == "Sonar"

    def test_artifact_fetch_error_returns_empty_on_invalid_uuid(self):
        """artifact_fetch_error with bad UUID → returns empty string."""
        rule_result = {"connector_instance_id": "not-a-uuid"}
        result = self.fn("artifact_fetch_error", rule_result, {}, {})
        assert result == ""

    def test_params_artifact_type_overrides_default(self):
        """Rule with explicit artifact_type in params takes precedence over RULE_DEFAULT_ARTIFACT_TYPES."""
        rule = self._make_rule(params={"artifact_type": "CODIGO"})
        artifact_type_connector = {"CODIGO": "GitHub", "TAREA": "Jira"}
        result = self.fn("RV-03", {}, {"RV-03": rule}, {}, artifact_type_connector)
        assert result == "GitHub"


# ── 10. _enrich_rule_results ─────────────────────────────────────────────────

class TestEnrichRuleResults:
    """Unit tests for rule_results._enrich_rule_results — no-connector override."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from features.verification.application.rule_results import _enrich_rule_results
        self.fn = _enrich_rule_results

    def _make_rule(self, connector_instance_id=None):
        from features.verification.domain.verification_rule import VerificationRule
        return VerificationRule(
            profile_id=uuid4(),
            rule_template="RV-03",
            connector_instance_id=connector_instance_id,
            params={},
        )

    def test_ok_with_no_connector_becomes_no_evaluada(self):
        """Rule returns OK but has no connector → status overridden to NO_EVALUADA."""
        rule = self._make_rule()
        result_data = {
            "rule_results": [{"rule_id": "RV-03", "status": "OK", "message": None}]
        }
        self.fn(result_data, {"RV-03": rule}, {}, {})
        rr = result_data["rule_results"][0]
        assert rr["status"] == "NO_EVALUADA"
        assert rr["evidence"] == "rule_evidence.no_connector"
        assert rr["connector"] == ""

    def test_ok_with_connector_stays_ok(self):
        """Rule returns OK and has a connector → status remains OK."""
        from uuid import uuid4
        cid = uuid4()
        rule = self._make_rule(connector_instance_id=cid)
        result_data = {
            "rule_results": [{"rule_id": "RV-03", "status": "OK", "message": None}]
        }
        self.fn(result_data, {"RV-03": rule}, {cid: "Jira"}, {})
        rr = result_data["rule_results"][0]
        assert rr["status"] == "OK"
        assert rr["connector"] == "Jira"

    def test_error_with_no_connector_becomes_no_evaluada(self):
        """Rule returns ERROR with no connector → status overridden to NO_EVALUADA too (no linked artifact means the rule was never actually evaluated)."""
        rule = self._make_rule()
        result_data = {
            "rule_results": [{"rule_id": "RV-03", "status": "ERROR", "message": "some error"}]
        }
        self.fn(result_data, {"RV-03": rule}, {}, {})
        rr = result_data["rule_results"][0]
        assert rr["status"] == "NO_EVALUADA"

    def test_rv01_always_shows_dash_and_keeps_status(self):
        """RV-01 checks artifact existence (no connector involved) → connector is always '-' and status is never overridden."""
        rule = self._make_rule()
        rule.rule_template = "RV-01"
        result_data = {
            "rule_results": [{"rule_id": "RV-01", "status": "OK", "message": None}]
        }
        self.fn(result_data, {"RV-01": rule}, {}, {})
        rr = result_data["rule_results"][0]
        assert rr["status"] == "OK"
        assert rr["connector"] == "-"

    def test_artifact_fetch_error_ok_not_overridden(self):
        """artifact_fetch_error entries with OK are never overridden regardless of connector."""
        result_data = {
            "rule_results": [{"rule_id": "artifact_fetch_error", "status": "OK", "message": None, "connector_instance_id": ""}]
        }
        self.fn(result_data, {}, {}, {})
        rr = result_data["rule_results"][0]
        assert rr["status"] == "OK"


# ── 11. _recompute_verdict ────────────────────────────────────────────────────

class TestRecomputeVerdict:
    """Regression guard: the verdict must be recomputed after _enrich_rule_results
    may downgrade a rule from ERROR to NO_EVALUADA (no linked artifact/connector).
    Otherwise the stored verdict stays NO_VALIDA from the engine's original
    (pre-downgrade) computation even though every visible rule is OK or gray."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from features.verification.application.rule_results import _recompute_verdict
        self.fn = _recompute_verdict

    def _make_rule(self, severity):
        from features.verification.domain.verification_rule import VerificationRule
        return VerificationRule(
            profile_id=uuid4(), rule_template="RV-03", params={}, severity=severity,
        )

    def test_only_ok_and_no_evaluada_is_valida_not_invalid(self):
        """The reported bug: an OBLIGATORIA rule downgraded ERROR->NO_EVALUADA must
        not leave the verdict as NO_VALIDA - the only real signal left is OK."""
        from shared.domain.enums import SeverityType
        rules = [self._make_rule(SeverityType.HIGH), self._make_rule(SeverityType.HIGH)]
        rule_results = [
            {"status": "OK"},
            {"status": "NO_EVALUADA"},
        ]
        assert self.fn(rule_results, rules) == "VALIDA"

    def test_mandatory_error_with_connector_stays_no_valida(self):
        from shared.domain.enums import SeverityType
        rules = [self._make_rule(SeverityType.HIGH)]
        rule_results = [{"status": "ERROR"}]
        assert self.fn(rule_results, rules) == "NO_VALIDA"

    def test_optional_error_gives_con_advertencias(self):
        from shared.domain.enums import SeverityType
        rules = [self._make_rule(SeverityType.HIGH), self._make_rule(SeverityType.LOW)]
        rule_results = [{"status": "OK"}, {"status": "ERROR"}]
        assert self.fn(rule_results, rules) == "CON_ADVERTENCIAS"

    def test_all_ok_is_valida(self):
        from shared.domain.enums import SeverityType
        rules = [self._make_rule(SeverityType.HIGH), self._make_rule(SeverityType.LOW)]
        rule_results = [{"status": "OK"}, {"status": "OK"}]
        assert self.fn(rule_results, rules) == "VALIDA"

    def test_duplicate_rule_template_matched_positionally(self):
        """Same template (RV-03) twice with different severities: the error on the
        second (OPCIONAL) instance must not be attributed to the first (OBLIGATORIA)."""
        from shared.domain.enums import SeverityType
        rules = [self._make_rule(SeverityType.HIGH), self._make_rule(SeverityType.LOW)]
        rule_results = [{"status": "OK"}, {"status": "ERROR"}]
        assert self.fn(rule_results, rules) == "CON_ADVERTENCIAS"
