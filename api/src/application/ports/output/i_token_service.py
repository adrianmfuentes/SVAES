from abc import ABC, abstractmethod
from uuid import UUID


class ITokenService(ABC):
    """Outbound port for managing authentication tokens.
    Keeps the application layer independent of the concrete token format (JWT, opaque, etc.).
    
    Methods:
        create_access_token(user_id: UUID, role: str) -> str: Generates an access token for a given user ID and role.
        decode_token(token: str) -> dict: Decodes the token and returns its payload as a dictionary.
    """

    @abstractmethod
    def create_access_token(self, user_id: UUID, role: str) -> str:
        pass

    @abstractmethod
    def decode_token(self, token: str) -> dict:
        pass
