from passlib.context import CryptContext
from application.ports.output.i_password_hasher import IPasswordHasher

"""
Este módulo define la clase `BcryptPasswordHasher`, que implementa la interfaz `IPasswordHasher` utilizando el algoritmo de hashing bcrypt 
a través de la biblioteca Passlib. La clase proporciona métodos para generar un hash a partir de una contraseña en texto plano y para 
verificar si una contraseña en texto plano coincide con un hash almacenado.
"""
class BcryptPasswordHasher(IPasswordHasher):
    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, plain: str) -> str:
        return self._ctx.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return self._ctx.verify(plain, hashed)
