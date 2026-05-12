"""Integration tests for artifact CRUD endpoints."""
import uuid

import pytest
from httpx import AsyncClient

from infrastructure.database.models.project import ProjectModel
from infrastructure.database.models.verification_profile import VerificationProfileModel
from infrastructure.database.models.release import ReleaseModel


async def _create_release(client: AsyncClient, db_session) -> str:
    """Helper: create minimal project + profile + release, return release_id."""
    from sqlalchemy import insert
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    release_id = uuid.uuid4()

    await db_session.execute(
        insert(ProjectModel).values(id=project_id, organization_id=org_id, name="P1", description="")
    )
    await db_session.execute(
        insert(VerificationProfileModel).values(id=profile_id, organization_id=org_id, name="Prof1")
    )
    await db_session.execute(
        insert(ReleaseModel).values(
            id=release_id,
            project_id=project_id,
            profile_id=profile_id,
            version="1.0.0",
            status="BORRADOR",
            created_by=uuid.uuid4(),
            description="",
        )
    )
    return str(release_id)


@pytest.mark.asyncio
async def test_register_and_list_artifacts(client: AsyncClient, db_session):
    release_id = await _create_release(client, db_session)
    base = f"/api/v1/releases/{release_id}/artifacts"

    resp = await client.post(
        base,
        json={"artifact_type": "CODIGO", "external_ref": "repo/main@abc123", "metadata": {"branch": "main"}},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["artifact_type"] == "CODIGO"
    assert data["release_id"] == release_id

    list_resp = await client.get(base)
    assert list_resp.status_code == 200
    assert any(a["id"] == data["id"] for a in list_resp.json())


@pytest.mark.asyncio
async def test_artifact_invalid_type_rejected(client: AsyncClient, db_session):
    release_id = await _create_release(client, db_session)
    base = f"/api/v1/releases/{release_id}/artifacts"

    resp = await client.post(
        base,
        json={"artifact_type": "INVALID_TYPE", "external_ref": "x"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_artifact(client: AsyncClient, db_session):
    release_id = await _create_release(client, db_session)
    base = f"/api/v1/releases/{release_id}/artifacts"

    create_resp = await client.post(base, json={"artifact_type": "TAREA", "external_ref": "TASK-1"})
    aid = create_resp.json()["id"]

    del_resp = await client.delete(f"{base}/{aid}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"{base}/{aid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_artifact_pagination(client: AsyncClient, db_session):
    release_id = await _create_release(client, db_session)
    base = f"/api/v1/releases/{release_id}/artifacts"

    for i in range(5):
        await client.post(base, json={"artifact_type": "PRUEBA", "external_ref": f"test-{i}"})

    resp = await client.get(f"{base}?skip=0&limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) <= 3
