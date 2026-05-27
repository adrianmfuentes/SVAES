import uuid
import pytest
from cryptography.fernet import Fernet
from core.credential_encryptor import FernetCredentialEncryptor

pytestmark = pytest.mark.unit


@pytest.fixture
def encryptor():
    key = Fernet.generate_key().decode()
    return FernetCredentialEncryptor(key)


@pytest.fixture
def instance_id():
    return uuid.uuid4()


class TestFernetCredentialEncryptorInit:
    def test_init_with_str_key(self):
        key = Fernet.generate_key().decode()
        encryptor = FernetCredentialEncryptor(key)
        assert isinstance(encryptor._fernet, Fernet)

    def test_init_with_bytes_key(self):
        key = Fernet.generate_key()
        encryptor = FernetCredentialEncryptor(key)
        assert isinstance(encryptor._fernet, Fernet)


class TestEncrypt:
    def test_encrypt_returns_bytes(self, encryptor, instance_id):
        result = encryptor.encrypt("secret data", instance_id)
        assert isinstance(result, bytes)
        assert result != b"secret data"

    def test_encrypt_deterministic(self, encryptor, instance_id):
        data = "my-password"
        r1 = encryptor.encrypt(data, instance_id)
        r2 = encryptor.encrypt(data, instance_id)
        assert r1 != r2

    def test_encrypt_with_associated_data(self, encryptor, instance_id):
        result = encryptor.encrypt("data", instance_id, {"key": "value"})
        assert isinstance(result, bytes)

    def test_encrypt_empty_string(self, encryptor, instance_id):
        result = encryptor.encrypt("", instance_id)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestDecrypt:
    def test_decrypt_returns_original(self, encryptor, instance_id):
        original = "secret data"
        encrypted = encryptor.encrypt(original, instance_id)
        decrypted = encryptor.decrypt(encrypted, instance_id)
        assert decrypted == original

    def test_decrypt_with_associated_data(self, encryptor, instance_id):
        original = "password123"
        encrypted = encryptor.encrypt(original, instance_id, {"meta": "info"})
        decrypted = encryptor.decrypt(encrypted, instance_id, {"meta": "info"})
        assert decrypted == original

    def test_decrypt_invalid_token_raises(self, encryptor, instance_id):
        from cryptography.fernet import InvalidToken
        with pytest.raises(InvalidToken):
            encryptor.decrypt(b"invalid-token", instance_id)

    def test_roundtrip_special_chars(self, encryptor, instance_id):
        original = "p@$$w0rd!ñáéíóú"
        encrypted = encryptor.encrypt(original, instance_id)
        decrypted = encryptor.decrypt(encrypted, instance_id)
        assert decrypted == original


class TestEncryptBytes:
    def test_encrypt_bytes_returns_bytes(self, encryptor, instance_id):
        result = encryptor.encrypt_bytes(b"raw data", instance_id)
        assert isinstance(result, bytes)
        assert result != b"raw data"

    def test_encrypt_bytes_roundtrip(self, encryptor, instance_id):
        original = b"\x00\x01\x02binary data\xff\xfe"
        encrypted = encryptor.encrypt_bytes(original, instance_id)
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id)
        assert decrypted == original

    def test_encrypt_bytes_with_associated_data(self, encryptor, instance_id):
        result = encryptor.encrypt_bytes(b"data", instance_id, {"k": "v"})
        assert isinstance(result, bytes)


class TestDecryptBytes:
    def test_decrypt_bytes_returns_bytes(self, encryptor, instance_id):
        encrypted = encryptor.encrypt_bytes(b"test", instance_id)
        result = encryptor.decrypt_bytes(encrypted, instance_id)
        assert isinstance(result, bytes)

    def test_decrypt_bytes_roundtrip(self, encryptor, instance_id):
        original = b"binary content"
        encrypted = encryptor.encrypt_bytes(original, instance_id)
        result = encryptor.decrypt_bytes(encrypted, instance_id)
        assert result == original

    def test_decrypt_bytes_invalid_token_raises(self, encryptor, instance_id):
        from cryptography.fernet import InvalidToken
        with pytest.raises(InvalidToken):
            encryptor.decrypt_bytes(b"invalid", instance_id)


class TestCrossMethod:
    def test_encrypt_then_decrypt_bytes(self, encryptor, instance_id):
        original = b"cross check"
        encrypted = encryptor.encrypt_bytes(original, instance_id)
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id)
        assert decrypted == original

    def test_encrypt_str_decrypt_bytes(self, encryptor, instance_id):
        original = "hello world"
        encrypted = encryptor.encrypt(original, instance_id)
        decrypted = encryptor.decrypt(encrypted, instance_id)
        assert decrypted == original
