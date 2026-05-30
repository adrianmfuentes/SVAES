import pytest
from core.pseudonymizer import pseudonymize

pytestmark = pytest.mark.unit


class TestPseudonymizeScalar:
    def test_string_unchanged(self):
        assert pseudonymize("hello") == "hello"

    def test_int_unchanged(self):
        assert pseudonymize(42) == 42

    def test_float_unchanged(self):
        assert pseudonymize(3.14) == pytest.approx(3.14)

    def test_none_unchanged(self):
        assert pseudonymize(None) is None

    def test_bool_unchanged(self):
        assert pseudonymize(True) is True


class TestPseudonymizeDict:
    def test_pii_keys_hashed(self):
        data = {"email": "test@example.com", "displayName": "John Doe"}
        result = pseudonymize(data)
        assert result["email"].startswith("sha256:")
        assert result["displayName"].startswith("sha256:")
        assert result["email"] != "test@example.com"
        assert result["displayName"] != "John Doe"

    def test_non_pii_keys_unchanged(self):
        data = {"id": "123", "title": "Hello", "count": 5}
        result = pseudonymize(data)
        assert result == {"id": "123", "title": "Hello", "count": 5}

    def test_empty_string_pii_value_not_hashed(self):
        data = {"email": ""}
        result = pseudonymize(data)
        assert result["email"] == ""

    def test_pii_value_is_dict_keeps_original(self):
        data = {"email": {"nested": "value"}, "name": "John"}
        result = pseudonymize(data)
        assert result["email"] == {"nested": "value"}
        assert result["name"].startswith("sha256:")

    def test_pii_value_is_list_keeps_original(self):
        data = {"email": ["test@example.com"], "name": "John"}
        result = pseudonymize(data)
        assert result["email"] == ["test@example.com"]
        assert result["name"].startswith("sha256:")

    def test_case_insensitive_pii_match(self):
        data = {"Email": "test@example.com", "USERNAME": "alice"}
        result = pseudonymize(data)
        assert result["Email"].startswith("sha256:")
        assert result["USERNAME"].startswith("sha256:")

    def test_mixed_pii_and_non_pii(self):
        data = {"email": "a@b.com", "title": "Bug", "author": "Jane"}
        result = pseudonymize(data)
        assert result["email"].startswith("sha256:")
        assert result["author"].startswith("sha256:")
        assert result["title"] == "Bug"

    def test_nested_dict_pii_in_both_levels(self):
        data = {"email": "outer@test.com", "nested": {"email": "inner@test.com", "count": 1}}
        result = pseudonymize(data)
        assert result["email"].startswith("sha256:")
        assert result["nested"]["email"].startswith("sha256:")
        assert result["nested"]["count"] == 1

    def test_all_known_pii_keys(self):
        pii_keys = [
            "email", "emailAddress", "displayName", "name", "username",
            "assignee", "reporter", "creator", "author", "accountId",
            "user", "owner", "login", "fullName", "firstName",
            "lastName", "avatarUrl", "profileUrl", "url",
        ]
        for key in pii_keys:
            data = {key: "sensitive-value"}
            result = pseudonymize(data)
            assert result[key].startswith("sha256:"), f"Key '{key}' was not pseudonymized"

    def test_hash_is_deterministic(self):
        value = "test@example.com"
        r1 = pseudonymize({"email": value})
        r2 = pseudonymize({"email": value})
        assert r1["email"] == r2["email"]


class TestPseudonymizeList:
    def test_list_of_dicts(self):
        data = [
            {"email": "a@test.com", "name": "Alice"},
            {"email": "b@test.com", "name": "Bob"},
        ]
        result = pseudonymize(data)
        assert len(result) == 2
        assert result[0]["email"].startswith("sha256:")
        assert result[0]["name"].startswith("sha256:")
        assert result[1]["email"].startswith("sha256:")
        assert result[1]["name"].startswith("sha256:")

    def test_list_of_scalars(self):
        data = [1, "hello", 3.14, None]
        result = pseudonymize(data)
        assert result == [1, "hello", pytest.approx(3.14), None]

    def test_empty_list(self):
        assert pseudonymize([]) == []

    def test_nested_lists(self):
        data = [{"items": [{"email": "a@b.com"}, {"email": "c@d.com"}]}]
        result = pseudonymize(data)
        assert result[0]["items"][0]["email"].startswith("sha256:")
        assert result[0]["items"][1]["email"].startswith("sha256:")


class TestPseudonymizeEdgeCases:
    def test_empty_dict(self):
        assert pseudonymize({}) == {}

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": {"email": "deep@test.com"}}}}
        result = pseudonymize(data)
        assert result["a"]["b"]["c"]["email"].startswith("sha256:")
