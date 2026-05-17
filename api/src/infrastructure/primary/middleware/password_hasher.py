import bcrypt
from application.ports.output.i_password_hasher import IPasswordHasher

class BcryptPasswordHasher(IPasswordHasher):
    def hash_password(self, plain: str) -> str:
        return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

    def needs_rehash(self, hashed: str) -> bool:
        return bcrypt.checkpw(None, hashed.encode('utf-8'))
