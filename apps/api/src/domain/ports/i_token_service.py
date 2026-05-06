from abc import ABC, abstractmethod
from uuid import UUID


class ITokenService(ABC):
    """Outbound port for issuing and decoding authentication tokens.

    Keeps the application layer independent of the concrete token format (JWT, opaque, etc.).
    """

    @abstractmethod
    def create_access_token(self, user_id: UUID, role: str) -> str:
        """Creates a signed access token embedding the user identity and role."""

    @abstractmethod
    def decode_token(self, token: str) -> dict:
        """Decodes and validates a token, returning its payload as a dict.

        Raises:
            Exception: if the token is invalid, malformed, or expired.
        """
