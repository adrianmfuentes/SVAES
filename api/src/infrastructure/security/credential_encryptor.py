from cryptography.fernet import Fernet
from domain.ports.i_credential_encryptor import ICredentialEncryptor

class FernetCredentialEncryptor(ICredentialEncryptor):
    """Implementation of ICredentialEncryptor using Fernet symmetric encryption. 
    This class provides methods to encrypt and decrypt credentials using a provided key.

    Methods:
        encrypt(data: str) -> bytes: Encrypts the given string data and returns the encrypted bytes.
        decrypt(data: bytes) -> str: Decrypts the given encrypted bytes and returns
    """

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, data: str) -> bytes:
        return self._fernet.encrypt(data.encode("utf-8"))

    def decrypt(self, data: bytes) -> str:
        return self._fernet.decrypt(data).decode("utf-8")
