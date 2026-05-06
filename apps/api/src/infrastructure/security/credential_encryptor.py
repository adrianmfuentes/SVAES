from cryptography.fernet import Fernet
from domain.ports.i_credential_encryptor import ICredentialEncryptor

class FernetCredentialEncryptor(ICredentialEncryptor):
    """AES-128-CBC (Fernet) implementation of ICredentialEncryptor.

    Fernet guarantees authenticated encryption — decryption will fail if the
    ciphertext has been tampered with, preventing silent data corruption.
    """

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, data: str) -> bytes:
        return self._fernet.encrypt(data.encode("utf-8"))

    def decrypt(self, data: bytes) -> str:
        return self._fernet.decrypt(data).decode("utf-8")
