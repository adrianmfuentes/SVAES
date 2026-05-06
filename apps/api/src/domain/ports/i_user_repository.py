from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.user import User

class IUserRepository(ABC):
    """
    Puerto de salida (Outbound Port): IUserRepository
    Define el contrato para la persistencia de la entidad User.
    Esencial para los casos de uso de Autenticación y Gestión de Usuarios.
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persiste un nuevo usuario en la base de datos."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Recupera un usuario por su identificador único."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Recupera un usuario por su correo electrónico.
        ¡Vital para el caso de uso de Login (autenticación)!
        """
        pass

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> List[User]:
        """Devuelve un listado de todos los usuarios registrados."""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Actualiza el estado, contraseña o datos de un usuario existente."""
        pass