from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    @abstractmethod
    def hash_password(self, plain: str) -> str:
        pass

    @abstractmethod
    def verify_password(self, plain: str, hashed: str) -> bool:
        pass

    @abstractmethod
    def needs_rehash(self, hashed: str) -> bool:
        pass