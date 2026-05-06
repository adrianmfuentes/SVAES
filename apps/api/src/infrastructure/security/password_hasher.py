from passlib.context import CryptContext
from domain.ports.i_password_hasher import IPasswordHasher

class BcryptPasswordHasher(IPasswordHasher):
    """bcrypt implementation of IPasswordHasher via passlib.

    Cost factor defaults to 12. Automatically handles deprecated schemes
    via passlib's deprecated='auto' policy.
    """

    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, plain: str) -> str:
        return self._ctx.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return self._ctx.verify(plain, hashed)
