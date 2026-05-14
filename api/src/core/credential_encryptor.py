import uuid
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet

from application.ports.output.i_credential_encryptor import ICredentialEncryptor


class FernetCredentialEncryptor(ICredentialEncryptor):
    """Implementation of ICredentialEncryptor using Fernet symmetric encryption.

    Fernet does not utilise ``instance_id`` or ``associated_data`` —
    those parameters are accepted for interface compliance only.
    """

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(
        self,
        data: str,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        return self._fernet.encrypt(data.encode("utf-8"))

    def decrypt(
        self,
        data: bytes,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self._fernet.decrypt(data).decode("utf-8")

    def encrypt_bytes(
        self,
        data: bytes,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(
        self,
        data: bytes,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        return self._fernet.decrypt(data)
