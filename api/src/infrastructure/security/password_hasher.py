from passlib.context import CryptContext
from domain.ports.i_password_hasher import IPasswordHasher

class BcryptPasswordHasher(IPasswordHasher):
    """Implementation of IPasswordHasher using bcrypt hashing algorithm. 
    This class provides methods to hash plaintext passwords and verify them against hashed versions.
    
    Methods:
        hash(plain: str) -> str: Hashes the given plaintext password and returns the hashed version.
        verify(plain: str, hashed: str) -> bool: Verifies that the given plaintext password matches the provided hashed password, returning True if they match and False otherwise.
    """

    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, plain: str) -> str:
        return self._ctx.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return self._ctx.verify(plain, hashed)
