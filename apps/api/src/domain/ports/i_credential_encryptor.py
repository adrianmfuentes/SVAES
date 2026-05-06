from abc import ABC, abstractmethod


class ICredentialEncryptor(ABC):
    """Outbound port for encrypting and decrypting connector credentials at rest.

    Ensures the application layer never handles raw encryption primitives.
    """

    @abstractmethod
    def encrypt(self, data: str) -> bytes:
        """Encrypts a plain-text credential string and returns cipher bytes."""

    @abstractmethod
    def decrypt(self, data: bytes) -> str:
        """Decrypts cipher bytes and returns the original plain-text string.

        Raises:
            Exception: if decryption fails (wrong key, corrupted data).
        """
