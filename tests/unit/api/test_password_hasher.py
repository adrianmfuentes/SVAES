import pytest
from unittest.mock import MagicMock
from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher():
    return BcryptPasswordHasher()


class TestHashPassword:
    def test_hash_password_returns_string(self, hasher):
        result = hasher.hash_password("my-password")
        assert isinstance(result, str)
        assert result.startswith("$2b$")

    def test_hash_password_different_for_same_input(self, hasher):
        r1 = hasher.hash_password("password")
        r2 = hasher.hash_password("password")
        assert r1 != r2

    def test_hash_password_empty_string(self, hasher):
        result = hasher.hash_password("")
        assert isinstance(result, str)


class TestVerifyPassword:
    def test_verify_correct_password(self, hasher):
        hashed = hasher.hash_password("correct-horse-battery-staple")
        assert hasher.verify_password("correct-horse-battery-staple", hashed) is True

    def test_verify_wrong_password(self, hasher):
        hashed = hasher.hash_password("original")
        assert hasher.verify_password("wrong", hashed) is False

    def test_verify_case_sensitive(self, hasher):
        hashed = hasher.hash_password("Password123")
        assert hasher.verify_password("password123", hashed) is False
        assert hasher.verify_password("Password123", hashed) is True


class TestNeedsRehash:
    def test_needs_rehash_default_rounds_12(self, hasher):
        hashed = hasher.hash_password("test")
        assert hasher.needs_rehash(hashed, 12) is False

    def test_needs_rehash_different_rounds(self, hasher):
        hashed = hasher.hash_password("test")
        assert hasher.needs_rehash(hashed, 14) is True
