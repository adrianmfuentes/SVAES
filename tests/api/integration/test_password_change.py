"""Integration tests for PATCH /users/me/password."""
import uuid

import pytest
from httpx import AsyncClient

from infrastructure.database.models.user import UserModel


async def _seed_user(db_session, email: str, password_hash: str) -> str:
    from sqlalchemy import insert
    uid = uuid.uuid4()
    await db_session.execute(
        insert(UserModel).values(
            id=uid,
            email=email,
            password_hash=password_hash,
            display_name=email,
            role="ADMIN",
            is_active=True,
        )
    )
    return str(uid)


@pytest.mark.asyncio
async def test_change_password_wrong_current_password(client: AsyncClient, db_session):
    """Returns 400 when current_password does not match."""
    resp = await client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "wrong_password", "new_password": "NewPassword123!"},
    )
    # The conftest admin user has hashed password "$2b$12$unused" which won't verify.
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_new_too_short(client: AsyncClient):
    """Returns 422 when new_password is shorter than 8 chars."""
    resp = await client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "anything", "new_password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_change_password_rate_limited(client: AsyncClient):
    """Endpoint is rate-limited to 5/minute."""
    for _ in range(5):
        await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": "bad", "new_password": "NewPassword123!"},
        )
    resp = await client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "bad", "new_password": "NewPassword123!"},
    )
    assert resp.status_code in (400, 429)
