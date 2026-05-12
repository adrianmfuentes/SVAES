from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """Outbound port for password hashing and verification. This interface defines the contract for securely hashing plain-text passwords 
    nd verifying them against stored hashes. Implementations of this interface can use various hashing algorithms (e.g., bcrypt, Argon2) 
    while the application layer interacts with it through these defined methods.    

    Methods:
        hash(plain: str) -> str: Returns a one-way hash of the plain-text password.
        verify(plain: str, hashed: str) -> bool: Returns True if plain
    """
    @abstractmethod
    def hash(self, plain: str) -> str:
        pass

    @abstractmethod
    def verify(self, plain: str, hashed: str) -> bool:
        pass
