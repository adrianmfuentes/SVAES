"""Integration tests for verification rule CRUD endpoints."""
import uuid

import pytest
from httpx import AsyncClient

from infrastructure.database.models.verification_profile import VerificationProfileModel


async def _create_profile(db_session) -> str:
    from sqlalchemy import insert
    org_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    await db_session.execute(
        insert(VerificationProfileModel).values(id=profile_id, organization_id=org_id, name="TestProfile")
    )
    return str(profile_id)


@pytest.mark.asyncio
async def test_create_and_list_rules(client: AsyncClient, db_session):
    profile_id = await _create_profile(db_session)
    base = f"/api/v1/profiles/{profile_id}/rules"

    resp = await client.post(
        base,
        json={"rule_template": "RV-01", "severity": "OBLIGATORIA", "display_order": 1},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["rule_template"] == "RV-01"
    assert data["profile_id"] == profile_id

    list_resp = await client.get(base)
    assert list_resp.status_code == 200
    assert any(r["id"] == data["id"] for r in list_resp.json())


@pytest.mark.asyncio
async def test_invalid_rule_template_rejected(client: AsyncClient, db_session):
    profile_id = await _create_profile(db_session)
    resp = await client.post(
        f"/api/v1/profiles/{profile_id}/rules",
        json={"rule_template": "RV-99", "severity": "OBLIGATORIA"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_rule(client: AsyncClient, db_session):
    profile_id = await _create_profile(db_session)
    base = f"/api/v1/profiles/{profile_id}/rules"

    create_resp = await client.post(base, json={"rule_template": "RV-02", "severity": "RECOMENDADA"})
    rid = create_resp.json()["id"]

    patch_resp = await client.patch(f"{base}/{rid}", json={"severity": "INFORMATIVA", "is_active": False})
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["severity"] == "INFORMATIVA"
    assert updated["is_active"] is False


@pytest.mark.asyncio
async def test_delete_rule(client: AsyncClient, db_session):
    profile_id = await _create_profile(db_session)
    base = f"/api/v1/profiles/{profile_id}/rules"

    create_resp = await client.post(base, json={"rule_template": "RV-03", "severity": "OBLIGATORIA"})
    rid = create_resp.json()["id"]

    del_resp = await client.delete(f"{base}/{rid}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{base}/{rid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_rule_wrong_profile_returns_404(client: AsyncClient, db_session):
    profile_a = await _create_profile(db_session)
    profile_b = await _create_profile(db_session)

    create_resp = await client.post(
        f"/api/v1/profiles/{profile_a}/rules",
        json={"rule_template": "RV-04", "severity": "OBLIGATORIA"},
    )
    rid = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/profiles/{profile_b}/rules/{rid}")
    assert resp.status_code == 404
