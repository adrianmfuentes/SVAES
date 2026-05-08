"""
Tests for FastAPI dependency functions.

Tests ``get_current_user`` by calling it directly with mocked credentials,
repository, and JWT handler — no HTTP layer needed.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from jwt.exceptions import InvalidTokenError
from api.dependencies import get_current_user
from domain.entities.user import User
from domain.entities.enums import UserRole


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$hashed", # NOSONAR
        role=UserRole.OPERATOR,
        organization_id=uuid.uuid4(),
    )


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self):
        user = _make_user()
        credentials = MagicMock()
        credentials.credentials = "valid.jwt.token"

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"sub": str(user.id)}

        result = await get_current_user(credentials, user_repo, jwt_handler)

        assert result is user

    async def test_invalid_token_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "bad.token.here"

        user_repo = AsyncMock()
        jwt_handler = MagicMock()
        jwt_handler.decode_token.side_effect = InvalidTokenError("expired")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401
        assert exc_info.value.headers is not None
        assert exc_info.value.headers.get("WWW-Authenticate") is not None

    async def test_missing_sub_claim_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "token.without.sub"

        user_repo = AsyncMock()
        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"role": "OPERATOR"}  # no 'sub'

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401

    async def test_invalid_uuid_in_sub_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "token.with.invalid.uuid"

        user_repo = AsyncMock()
        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"sub": "not-a-valid-uuid"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401

    async def test_user_not_found_raises_401(self):
        user_id = uuid.uuid4()
        credentials = MagicMock()
        credentials.credentials = "valid.token"

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = None

        jwt_handler = MagicMock()
        jwt_handler.decode_token.return_value = {"sub": str(user_id)}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, user_repo, jwt_handler)

        assert exc_info.value.status_code == 401
        assert "Usuario no encontrado" in exc_info.value.detail
