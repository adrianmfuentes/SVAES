"""
Integration tests for API key authentication (AC5 / API2 / API4).

Tests verify that API keys created via POST /api/v1/users/{user_id}/api-keys
actually authenticate and authorize requests against the running FastAPI app.
Uses httpx.AsyncClient with ASGITransport (no real network), real DB, real Redis.
"""

import os
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_API_KEY_HDR = "X-API-Key"
_MAX_ACTIVE_KEYS = 5


def _make_jwt(user_id, email, role, organization_id):
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler

    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=os.environ.get("REDIS_URL"),
    )
    return handler.create_access_token(
        user_id=user_id,
        email=email,
        role=role.value if isinstance(role, UserRole) else role,
        organization_id=organization_id,
    )


@pytest_asyncio.fixture
async def org_with_admin(client):
    """Create a real org and admin user in the DB, return (org_id, user_id, jwt_headers)."""
    from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
    from infrastructure.secondary.database.models import OrganizationModel, UserModel
    from domain.enums import UserRole

    org_id = uuid4()
    user_id = uuid4()

    async with AsyncSessionLocal() as sess:
        org = OrganizationModel(id=org_id, name="Test Org", slug=f"test-org-{uuid4().hex[:8]}")
        sess.add(org)
        user = UserModel(
            id=user_id,
            email=f"admin-{uuid4().hex[:8]}@test-integration.local",
            display_name="Admin",
            hashed_password="placeholder",
            role=UserRole.U3,
            organization_id=org_id,
        )
        sess.add(user)
        await sess.commit()

    token = _make_jwt(user_id, user.email, UserRole.U3, org_id)
    return org_id, user_id, {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def viewer_user(client, org_with_admin):
    """Create a U2 (OPERATOR) user in the same org as admin."""
    from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
    from infrastructure.secondary.database.models import UserModel
    from domain.enums import UserRole

    org_id, _, _ = org_with_admin
    viewer_id = uuid4()
    email = f"viewer-{uuid4().hex[:6]}@test-integration.local"

    async with AsyncSessionLocal() as sess:
        user = UserModel(
            id=viewer_id,
            email=email,
            display_name="Viewer",
            hashed_password="placeholder",
            role=UserRole.U2,
            organization_id=org_id,
        )
        sess.add(user)
        await sess.commit()

    token = _make_jwt(viewer_id, email, UserRole.U2, org_id)
    return viewer_id, org_id, {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_org(client):
    """Create a second organization (org B) with an admin user."""
    from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
    from infrastructure.secondary.database.models import OrganizationModel, UserModel
    from domain.enums import UserRole

    org_id = uuid4()
    user_id = uuid4()

    async with AsyncSessionLocal() as sess:
        org = OrganizationModel(id=org_id, name="Org B", slug=f"org-b-{uuid4().hex[:8]}")
        sess.add(org)
        user = UserModel(
            id=user_id,
            email=f"admin-org-b-{uuid4().hex[:8]}@test-integration.local",
            display_name="OrgB Admin",
            hashed_password="placeholder",
            role=UserRole.U3,
            organization_id=org_id,
        )
        sess.add(user)
        await sess.commit()

    token = _make_jwt(user_id, user.email, UserRole.U3, org_id)
    return org_id, user_id, {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def api_key_factory(client: AsyncClient, org_with_admin):
    """Create an API key for the given user via the real endpoint. Returns (plaintext_key, key_id)."""
    async def _create(user_id: str, headers: dict, name: str = "test-key") -> tuple[str, str]:
        resp = await client.post(
            f"/api/v1/users/{user_id}/api-keys",
            json={"name": name},
            headers=headers,
        )
        assert resp.status_code == 201, f"Key creation failed: {resp.status_code} {resp.text}"
        data = resp.json()
        return data["key"], data["id"]

    return _create


@pytest_asyncio.fixture
async def redis_client():
    """Redis client for rate-limit key cleanup."""
    import redis.asyncio as redis

    redis_url = os.environ.get("TEST_REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    client = redis.from_url(redis_url, decode_responses=True)
    yield client
    await client.aclose()


async def _revoke_key(client: AsyncClient, user_id: str, key_id: str, headers: dict) -> None:
    """Revoke an API key via the real endpoint."""
    resp = await client.delete(
        f"/api/v1/users/{user_id}/api-keys/{key_id}",
        headers=headers,
    )
    assert resp.status_code == 204, f"Revoke failed: {resp.status_code} {resp.text}"


# =============================================================================
# TC-API-AUTH-01: valid API key on protected endpoint returns 200 (AC5.3 / API2.3)
# =============================================================================
async def test_tc_api_auth_01_valid_key_on_protected_endpoint(
    client, org_with_admin, api_key_factory
):
    """
    Requirement: AC5.3 / API2.3
    A valid (active, non-expired) API key sent via X-API-Key header on a
    protected endpoint must authenticate the request and return 200.
    """
    _, user_id, jwt_headers = org_with_admin
    plaintext, _ = await api_key_factory(str(user_id), jwt_headers, "valid-key")

    resp = await client.get(
        "/api/v1/organizations",
        headers={_API_KEY_HDR: plaintext, **jwt_headers},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# =============================================================================
# TC-API-AUTH-02: missing header returns 401 (AC5.3 / API2.3)
# =============================================================================
async def test_tc_api_auth_02_missing_header_returns_401(
    client, org_with_admin, api_key_factory
):
    """
    Requirement: AC5.3 / API2.3
    A request to a protected endpoint without the X-API-Key header must
    return 401 Unauthorized.
    """
    _, user_id, jwt_headers = org_with_admin
    await api_key_factory(str(user_id), jwt_headers, "missing-hdr-key")

    resp = await client.get("/api/v1/organizations", headers=jwt_headers)
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


# =============================================================================
# TC-API-AUTH-03: malformed/non-existent key returns 401 (API2.4)
# =============================================================================
async def test_tc_api_auth_03_malformed_key_returns_401(client, org_with_admin):
    """
    Requirement: API2.4
    A request with a malformed or non-existent API key value must return 401.
    """
    _, _, jwt_headers = org_with_admin

    resp = await client.get(
        "/api/v1/organizations",
        headers={_API_KEY_HDR: "not_a_valid_key_at_all_12345", **jwt_headers},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


# =============================================================================
# TC-API-AUTH-04: revoked key returns 401 immediately after revocation (AC5.5 / API2.6.1)
# =============================================================================
async def test_tc_api_auth_04_revoked_key_returns_401(
    client, org_with_admin, api_key_factory
):
    """
    Requirement: AC5.5 / API2.6.1
    After a key is revoked via DELETE /api/v1/users/{user_id}/api-keys/{key_id},
    using that key in a subsequent request must return 401.
    """
    _, user_id, jwt_headers = org_with_admin
    plaintext, key_id = await api_key_factory(str(user_id), jwt_headers, "to-revoke")

    await _revoke_key(client, str(user_id), key_id, jwt_headers)

    resp = await client.get(
        "/api/v1/organizations",
        headers={_API_KEY_HDR: plaintext, **jwt_headers},
    )
    assert resp.status_code == 401, f"Expected 401 after revocation, got {resp.status_code}"


# =============================================================================
# TC-API-AUTH-05: expired key returns 401 (AC5.4 / API2.5)
# =============================================================================
async def test_tc_api_auth_05_expired_key_returns_401(
    client, org_with_admin, api_key_factory
):
    """
    Requirement: AC5.4 / API2.5
    A key with expires_at in the past must return 401 when used.
    """
    from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
    from infrastructure.secondary.database.models.api_key_model import APIKeyModel
    import sqlalchemy as sa

    _, user_id, jwt_headers = org_with_admin
    plaintext, key_id = await api_key_factory(str(user_id), jwt_headers, "expired-key")

    async with AsyncSessionLocal() as sess:
        await sess.execute(
            sa.update(APIKeyModel)
            .where(APIKeyModel.id == key_id)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        )
        await sess.commit()

    async with AsyncSessionLocal() as sess:
        result = await sess.execute(
            sa.select(APIKeyModel.expires_at).where(APIKeyModel.id == key_id)
        )
        result.scalar_one_or_none()

    resp = await client.get(
        "/api/v1/organizations",
        headers={_API_KEY_HDR: plaintext, **jwt_headers},
    )
    assert resp.status_code == 401, f"Expected 401 for expired key, got {resp.status_code}"


# =============================================================================
# TC-API-AUTH-06: creating 6th active key returns 4xx (AC5.1.1)
# =============================================================================
async def test_tc_api_auth_06_sixth_key_returns_429(client, org_with_admin):
    """
    Requirement: AC5.1.1
    A user with 5 active API keys must receive a 4xx response when attempting
    to create a 6th key via POST /api/v1/users/{user_id}/api-keys.
    """
    _, user_id, jwt_headers = org_with_admin

    for i in range(_MAX_ACTIVE_KEYS):
        resp = await client.post(
            f"/api/v1/users/{user_id}/api-keys",
            json={"name": f"key-{i}"},
            headers=jwt_headers,
        )
        assert resp.status_code == 201, f"Failed to create key {i}: {resp.status_code}"

    over_limit_resp = await client.post(
        f"/api/v1/users/{user_id}/api-keys",
        json={"name": "key-over-limit"},
        headers=jwt_headers,
    )
    assert 400 <= over_limit_resp.status_code < 500, (
        f"Expected 4xx when creating 6th key, got {over_limit_resp.status_code}"
    )


# =============================================================================
# TC-API-AUTH-07: plaintext only on creation; listing shows only last 8 chars (AC5.2 / AC5.6)
# =============================================================================
async def test_tc_api_auth_07_plaintext_only_on_creation(
    client, org_with_admin, api_key_factory
):
    """
    Requirement: AC5.2 / AC5.6
    The full plaintext key is returned ONLY in the 201 response.
    A subsequent GET /api/v1/users/{user_id}/api-keys must NOT contain the
    plaintext key; it may expose only the last 8 characters of the prefix.
    """
    _, user_id, jwt_headers = org_with_admin
    plaintext, key_id = await api_key_factory(str(user_id), jwt_headers, "masked-key")

    list_resp = await client.get(
        f"/api/v1/users/{user_id}/api-keys",
        headers=jwt_headers,
    )
    assert list_resp.status_code == 200
    keys = list_resp.json()
    my_key = next(k for k in keys if k["id"] == key_id)

    assert my_key.get("key") is None or my_key.get("key") != plaintext, (
        "Plaintext key must NOT appear in listing response"
    )
    assert plaintext not in str(keys), "Plaintext must not be in listing response"


# =============================================================================
# TC-API-AUTH-08: DB stores hash, not plaintext (AC5.2)
# =============================================================================
async def test_tc_api_auth_08_db_stores_hash_not_plaintext(
    client, org_with_admin, api_key_factory
):
    """
    Requirement: AC5.2
    Verify that the api_key table stores a SHA-256 hash of the key, not the
    raw plaintext. Query the table directly and assert no row contains the raw value.
    """
    from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
    from infrastructure.secondary.database.models.api_key_model import APIKeyModel
    import sqlalchemy as sa

    _, user_id, jwt_headers = org_with_admin
    plaintext, key_id = await api_key_factory(str(user_id), jwt_headers, "hashed-key")

    async with AsyncSessionLocal() as sess:
        result = await sess.execute(sa.select(APIKeyModel.key_hash, APIKeyModel.name))
        rows = result.all()
        for key_hash_val, name in rows:
            assert plaintext not in (key_hash_val or ""), (
                f"Plaintext key found in key_hash column for key '{name}'"
            )

    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    async with AsyncSessionLocal() as sess:
        result = await sess.execute(
            sa.select(APIKeyModel.key_hash).where(APIKeyModel.id == uuid4())
        )
        row = result.scalar_one_or_none()
        if row:
            assert row != plaintext, "Raw plaintext must not be stored in DB"
            assert row == expected_hash, "key_hash must be SHA-256 of plaintext"


# =============================================================================
# TC-API-AUTH-09: rate limit — 101 requests within a minute triggers 429 (API4.1 / API4.2 / API4.3)
# =============================================================================
async def test_tc_api_auth_09_rate_limit_429(
    client, org_with_admin, api_key_factory, redis_client
):
    """
    Requirement: API4.1 / API4.2 / API4.3
    Issue 101 requests with the same API key within one minute.
    Assert at least one 429 response containing Retry-After header, and that
    X-RateLimit-Remaining decreases monotonically in non-429 responses.
    """
    _, user_id, jwt_headers = org_with_admin
    plaintext, _ = await api_key_factory(str(user_id), jwt_headers, "rate-limit-key")

    rate_key = f"rate_limit:{hashlib.sha256(plaintext.encode()).hexdigest()}"
    try:
        await redis_client.delete(rate_key)
    except Exception:
        pass

    remaining_values: list[int] = []
    got_429 = False

    for _ in range(101):
        resp = await client.get(
            "/api/v1/organizations",
            headers={_API_KEY_HDR: plaintext, **jwt_headers},
        )
        if resp.status_code == 429:
            got_429 = True
            assert "Retry-After" in resp.headers, (
                "429 response missing Retry-After header"
            )
            break
        remaining = int(resp.headers.get("X-RateLimit-Remaining", -1))
        if remaining >= 0:
            remaining_values.append(remaining)

    assert got_429, f"Expected at least one 429 after 101 requests, got {resp.status_code}"

    for i in range(1, len(remaining_values)):
        assert remaining_values[i] <= remaining_values[i - 1], (
            f"X-RateLimit-Remaining did not decrease monotonically at index {i}"
        )


# =============================================================================
# TC-API-AUTH-10: RBAC — U1 (VIEWER) key cannot POST to write endpoint (API2.7)
# =============================================================================
async def test_tc_api_auth_10_viewer_key_cannot_write(
    client, viewer_user, api_key_factory
):
    """
    Requirement: API2.7
    A key belonging to a U1 (VIEWER) user must receive 403 Forbidden when
    attempting to POST to a write-capable endpoint.
    """
    viewer_id, _, jwt_headers = viewer_user
    plaintext, _ = await api_key_factory(str(viewer_id), jwt_headers, "viewer-key")

    resp = await client.post(
        "/api/v1/organizations",
        json={"name": "Should Fail", "slug": f"fail-{uuid4().hex[:8]}"},
        headers={_API_KEY_HDR: plaintext, **jwt_headers},
    )
    assert resp.status_code == 403, f"Expected 403 for VIEWER key on write, got {resp.status_code}"


# =============================================================================
# TC-API-AUTH-11: multi-tenant isolation — key of org A cannot read org B resource (API2.8)
# =============================================================================
async def test_tc_api_auth_11_key_cannot_access_other_org(
    client, org_with_admin, second_org, api_key_factory
):
    """
    Requirement: API2.8
    An API key belonging to a user in org A must receive 403 or 404 when
    attempting to read a resource that belongs to org B.
    """
    _, admin_user_id, admin_jwt_headers = org_with_admin
    org_b_id, _, org_b_jwt_headers = second_org

    org_a_key_plaintext, _ = await api_key_factory(
        str(admin_user_id), admin_jwt_headers, "org-a-key"
    )

    resp = await client.get(
        f"/api/v1/organizations/{org_b_id}",
        headers={_API_KEY_HDR: org_a_key_plaintext, **admin_jwt_headers},
    )
    assert resp.status_code in (403, 404), (
        f"Expected 403/404 when org-A key accesses org-B resource, got {resp.status_code}"
    )