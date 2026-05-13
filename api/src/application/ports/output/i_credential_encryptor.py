from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import uuid


class ICredentialEncryptor(ABC):
    @abstractmethod
    def encrypt(
        self,
        data: str,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        pass

    @abstractmethod
    def decrypt(
        self,
        data: bytes,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        pass

    @abstractmethod
    def encrypt_bytes(
        self,
        data: bytes,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        pass

    @abstractmethod
    def decrypt_bytes(
        self,
        data: bytes,
        instance_id: uuid.UUID,
        associated_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        pass