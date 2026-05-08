from abc import ABC, abstractmethod


class ICredentialEncryptor(ABC):
    """Outbound port for encrypting and decrypting sensitive credential data. This interface abstracts the encryption mechanism, 
    allowing the application layer to securely handle credentials without being coupled to a specific encryption library or algorithm. 
    Implementations of this interface can use symmetric encryption, asymmetric encryption, or any other method as needed, while the 
    application layer simply calls encrypt and decrypt methods.

    Methods:
        encrypt(data: str) -> bytes: Encrypts a plain-text credential string and returns cipher
        decrypt(data: bytes) -> str: Decrypts cipher bytes and returns the original plain-text string.
    """
    @abstractmethod
    def encrypt(self, data: str) -> bytes:
        pass

    @abstractmethod
    def decrypt(self, data: bytes) -> str:
        pass
