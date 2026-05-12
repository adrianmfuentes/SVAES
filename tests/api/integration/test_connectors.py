"""Integration tests for connector CRUD endpoints."""
import uuid

import pytest
from httpx import AsyncClient


ORG_ID = uuid.uuid4()
BASE = f"/api/v1/organizations/{ORG_ID}/connectors"


@pytest.mark.asyncio
async def test_create_and_get_connector(client: AsyncClient):
    payload = {
        "connector_type": "JIRA",
        "name": "My Jira",
        "config_data": {"url": "https://jira.example.com", "token": "secret"},
    }
    resp = await client.post(BASE, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "My Jira"
    assert data["connector_type"] == "JIRA"
    assert "config_encrypted" not in data
    assert "encrypted_credentials" not in data

    cid = data["id"]
    resp2 = await client.get(f"{BASE}/{cid}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == cid


@pytest.mark.asyncio
async def test_list_connectors_pagination(client: AsyncClient):
    org_id = uuid.uuid4()
    base = f"/api/v1/organizations/{org_id}/connectors"
    for i in range(3):
        await client.post(
            base,
            json={
                "connector_type": "JIRA",
                "name": f"Connector {i}",
                "config_data": {"token": f"t{i}"},
            },
        )
    resp = await client.get(f"{base}?include_inactive=true&skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2

    resp2 = await client.get(f"{base}?include_inactive=true&skip=2&limit=10")
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_get_connector_wrong_org_returns_404(client: AsyncClient):
    org_a = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/organizations/{org_a}/connectors",
        json={"connector_type": "JIRA", "name": "A", "config_data": {"token": "x"}},
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    org_b = uuid.uuid4()
    resp2 = await client.get(f"/api/v1/organizations/{org_b}/connectors/{cid}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_connector(client: AsyncClient):
    org_id = uuid.uuid4()
    base = f"/api/v1/organizations/{org_id}/connectors"
    resp = await client.post(
        base, json={"connector_type": "JIRA", "name": "ToDelete", "config_data": {"token": "t"}}
    )
    cid = resp.json()["id"]

    del_resp = await client.delete(f"{base}/{cid}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{base}/{cid}")
    assert get_resp.status_code == 404
