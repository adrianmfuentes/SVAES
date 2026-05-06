from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """Outbound port for password hashing and constant-time verification.

    Decouples the application layer from the concrete hashing algorithm (bcrypt, argon2, etc.).
    """

    @abstractmethod
    def hash(self, plain: str) -> str:
        """Returns a one-way hash of the plain-text password."""

    @abstractmethod
    def verify(self, plain: str, hashed: str) -> bool:
        """Returns True if plain matches the stored hash. Always runs in constant time."""
