"""
Tests for infrastructure security implementations, adapters, logging, and config.
"""

import uuid
import logging
import pytest
from cryptography.fernet import Fernet

from infrastructure.security.jwt_handler import JwtHandler
from infrastructure.security.credential_encryptor import FernetCredentialEncryptor
from infrastructure.security.mock_task_queue import MockTaskQueue
from infrastructure.adapters.connector_registry import ConnectorRegistry
from infrastructure.logging.logger import _configure_root_logger, get_logger
from infrastructure.config import Settings


_TEST_SECRET = "test-unit-secret-key-for-jwt-tests"
_TEST_FERNET_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# JwtHandler
# ---------------------------------------------------------------------------

class TestJwtHandler:
    def test_create_access_token_returns_non_empty_string(self):
        handler = JwtHandler(secret=_TEST_SECRET)
        token = handler.create_access_token(user_id=uuid.uuid4(), role="OPERATOR")

        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_returns_correct_sub_and_role(self):
        handler = JwtHandler(secret=_TEST_SECRET)
        user_id = uuid.uuid4()

        token = handler.create_access_token(user_id=user_id, role="ADMIN")
        payload = handler.decode_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["role"] == "ADMIN"

    def test_decode_invalid_token_raises(self):
        from jwt.exceptions import InvalidTokenError
        handler = JwtHandler(secret=_TEST_SECRET)

        with pytest.raises(InvalidTokenError):
            handler.decode_token("this.is.not.a.valid.jwt")

    def test_token_from_different_secret_rejected(self):
        from jwt.exceptions import InvalidTokenError
        signer = JwtHandler(secret="secret-a")
        verifier = JwtHandler(secret="secret-b")

        token = signer.create_access_token(user_id=uuid.uuid4(), role="VIEWER")

        with pytest.raises(InvalidTokenError):
            verifier.decode_token(token)

    def test_custom_algorithm_stored(self):
        handler = JwtHandler(secret=_TEST_SECRET, algorithm="HS256", expire_minutes=30)
        user_id = uuid.uuid4()

        token = handler.create_access_token(user_id=user_id, role="MANAGER")
        payload = handler.decode_token(token)

        assert payload["sub"] == str(user_id)

    def test_decoded_payload_has_iat_and_exp(self):
        handler = JwtHandler(secret=_TEST_SECRET)
        token = handler.create_access_token(user_id=uuid.uuid4(), role="OPERATOR")
        payload = handler.decode_token(token)

        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]


# ---------------------------------------------------------------------------
# FernetCredentialEncryptor
# ---------------------------------------------------------------------------

class TestFernetCredentialEncryptor:
    def test_encrypt_returns_bytes(self):
        enc = FernetCredentialEncryptor(key=_TEST_FERNET_KEY)
        result = enc.encrypt("secret_value")

        assert isinstance(result, bytes)
        assert result != b"secret_value"

    def test_roundtrip_preserves_data(self):
        enc = FernetCredentialEncryptor(key=_TEST_FERNET_KEY)
        original = '{"token": "ghp_abc123", "host": "github.com"}'

        ciphertext = enc.encrypt(original)
        plaintext = enc.decrypt(ciphertext)

        assert plaintext == original

    def test_accepts_bytes_key(self):
        key_bytes = Fernet.generate_key()
        enc = FernetCredentialEncryptor(key=key_bytes)  # type: ignore[arg-type]

        data = "some credentials"
        assert enc.decrypt(enc.encrypt(data)) == data

    def test_different_keys_produce_different_ciphertext(self):
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()
        enc1 = FernetCredentialEncryptor(key=key1)
        enc2 = FernetCredentialEncryptor(key=key2)

        ct1 = enc1.encrypt("data")
        ct2 = enc2.encrypt("data")

        assert ct1 != ct2


# ---------------------------------------------------------------------------
# MockTaskQueue
# ---------------------------------------------------------------------------

class TestMockTaskQueue:
    async def test_enqueue_returns_uuid_string(self):
        queue = MockTaskQueue()
        task_id = await queue.enqueue_verification_task(uuid.uuid4())

        assert isinstance(task_id, str)
        uuid.UUID(task_id)  # raises if not valid UUID format

    async def test_enqueue_returns_unique_ids_each_call(self):
        queue = MockTaskQueue()
        release_id = uuid.uuid4()

        id1 = await queue.enqueue_verification_task(release_id)
        id2 = await queue.enqueue_verification_task(release_id)

        assert id1 != id2

    async def test_get_task_status_returns_pending(self):
        queue = MockTaskQueue()
        status = await queue.get_task_status("any-task-id-here")

        assert status == "PENDING"

    async def test_get_task_status_any_id(self):
        queue = MockTaskQueue()
        status = await queue.get_task_status(str(uuid.uuid4()))

        assert status == "PENDING"


# ---------------------------------------------------------------------------
# ConnectorRegistry
# ---------------------------------------------------------------------------

class TestConnectorRegistry:
    def test_register_and_retrieve(self):
        registry = ConnectorRegistry()
        connector = object()

        registry.register("github", connector)

        assert registry.get_connector("github") is connector

    def test_unregistered_type_raises_key_error(self):
        registry = ConnectorRegistry()

        with pytest.raises(KeyError, match="not registered"):
            registry.get_connector("unknown_type")

    def test_overwrite_registration(self):
        registry = ConnectorRegistry()
        old = object()
        new = object()

        registry.register("jira", old)
        registry.register("jira", new)

        assert registry.get_connector("jira") is new

    def test_multiple_connectors_independent(self):
        registry = ConnectorRegistry()
        gh = object()
        jira = object()

        registry.register("github", gh)
        registry.register("jira", jira)

        assert registry.get_connector("github") is gh
        assert registry.get_connector("jira") is jira

    def test_error_message_includes_type(self):
        registry = ConnectorRegistry()

        with pytest.raises(KeyError) as exc_info:
            registry.get_connector("sonarqube")

        assert "sonarqube" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class TestLogging:
    def test_configure_root_logger_runs_idempotently(self):
        _configure_root_logger()
        _configure_root_logger()  # second call should be a no-op

    def test_get_logger_returns_logger_instance(self):
        logger = get_logger("test.module.name")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module.name"

    def test_get_logger_is_cached(self):
        logger1 = get_logger("cached.test.module")
        logger2 = get_logger("cached.test.module")

        assert logger1 is logger2

    def test_different_names_give_different_loggers(self):
        logger_a = get_logger("module.a")
        logger_b = get_logger("module.b")

        assert logger_a is not logger_b


# ---------------------------------------------------------------------------
# Settings / Config
# ---------------------------------------------------------------------------

class TestSettings:
    def test_auto_generates_fernet_key_when_empty(self):
        settings = Settings(encryption_key="")

        assert settings.encryption_key != ""
        # Verify it's a valid Fernet key
        Fernet(settings.encryption_key.encode())

    def test_explicit_encryption_key_preserved(self):
        key = Fernet.generate_key().decode()
        settings = Settings(encryption_key=key)

        assert settings.encryption_key == key

    def test_default_jwt_algorithm_is_hs256(self):
        settings = Settings()

        assert settings.jwt_algorithm == "HS256"

    def test_default_expire_minutes(self):
        settings = Settings()

        assert settings.jwt_expire_minutes == 60

    def test_custom_jwt_secret(self):
        settings = Settings(jwt_secret_key="my-custom-secret")  # NOSONAR

        assert settings.jwt_secret_key == "my-custom-secret"


# ---------------------------------------------------------------------------
# BcryptPasswordHasher
# ---------------------------------------------------------------------------

class TestBcryptPasswordHasher:
    def test_init_creates_bcrypt_context(self):
        from unittest.mock import patch, MagicMock
        from infrastructure.security.password_hasher import BcryptPasswordHasher
        with patch("infrastructure.security.password_hasher.CryptContext") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value = mock_ctx

            hasher = BcryptPasswordHasher()

            mock_cls.assert_called_once_with(schemes=["bcrypt"], deprecated="auto")
            assert hasher._ctx is mock_ctx

    def test_hash_delegates_to_ctx(self):
        from unittest.mock import patch, MagicMock
        from infrastructure.security.password_hasher import BcryptPasswordHasher
        with patch("infrastructure.security.password_hasher.CryptContext") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.hash.return_value = "$2b$12$hashed"  # NOSONAR
            mock_cls.return_value = mock_ctx

            result = BcryptPasswordHasher().hash("secret")  # NOSONAR

            assert result == "$2b$12$hashed"  # NOSONAR
            mock_ctx.hash.assert_called_once_with("secret")  # NOSONAR

    def test_verify_delegates_to_ctx(self):
        from unittest.mock import patch, MagicMock
        from infrastructure.security.password_hasher import BcryptPasswordHasher
        with patch("infrastructure.security.password_hasher.CryptContext") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.verify.return_value = True
            mock_cls.return_value = mock_ctx

            result = BcryptPasswordHasher().verify("plain", "$2b$12$hashed")  # NOSONAR

            assert result is True
            mock_ctx.verify.assert_called_once_with("plain", "$2b$12$hashed")  # NOSONAR


# ---------------------------------------------------------------------------
# DatabaseSession
# ---------------------------------------------------------------------------

class TestDatabaseSession:
    def test_get_engine_returns_session_factory(self):
        from unittest.mock import patch, MagicMock
        import infrastructure.database.session as session_module

        mock_engine = MagicMock()
        mock_factory = MagicMock()

        with patch("infrastructure.database.session.create_async_engine", return_value=mock_engine), \
             patch("infrastructure.database.session.async_sessionmaker", return_value=mock_factory):
            # Reset singleton state so the mocked path is exercised
            session_module._engine = None
            session_module._AsyncSessionLocal = None

            from infrastructure.database.session import _get_engine
            factory = _get_engine()

        assert factory is mock_factory

    def test_get_engine_returns_same_instance_on_repeated_calls(self):
        from unittest.mock import patch, MagicMock
        import infrastructure.database.session as session_module

        mock_engine = MagicMock()
        mock_factory = MagicMock()

        with patch("infrastructure.database.session.create_async_engine", return_value=mock_engine), \
             patch("infrastructure.database.session.async_sessionmaker", return_value=mock_factory):
            session_module._engine = None
            session_module._AsyncSessionLocal = None

            from infrastructure.database.session import _get_engine
            factory1 = _get_engine()
            factory2 = _get_engine()

        assert factory1 is factory2
        assert factory1 is mock_factory
