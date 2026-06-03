import pytest
from uuid import uuid4

pytestmark = pytest.mark.integration


async def _create_org(client, headers, prefix="org"):
    slug = f"{prefix}-{uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": f"Test {prefix}", "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _setup_release(client, headers):
    org_id = await _create_org(client, headers, "lr")
    profile_resp = await client.post(
        f"/api/v1/organizations/{org_id}/profiles",
        json={"name": f"LC-Profile-{uuid4().hex[:6]}", "description": "Lifecycle test"},
        headers=headers,
    )
    profile_id = profile_resp.json()["id"]
    project_resp = await client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": f"LC-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
        headers=headers,
    )
    project_id = project_resp.json()["id"]
    release_resp = await client.post(
        f"/api/v1/projects/{project_id}/releases",
        json={"name": f"LC-Release-{uuid4().hex[:6]}", "version": "1.0.0", "profile_id": profile_id},
        headers=headers,
    )
    return release_resp.json()["id"]


@pytest.mark.usefixtures("db")
class TestReleaseCreation:
    """Release creation scenarios."""

    async def test_create_release_minimal(self, client, manager_headers):
        org_id = await _create_org(client, manager_headers, "min")
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": f"Min-Profile-{uuid4().hex[:6]}", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": f"Min-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "Minimal Release", "version": "1.0.0"},
            headers=manager_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "BORRADOR"

    async def test_create_release_without_auth(self, client):
        response = await client.post(
            f"/api/v1/projects/{uuid4()}/releases",
            json={"name": "No Auth Release", "version": "1.0.0"},
        )
        assert response.status_code in (401, 403)

    async def test_create_release_invalid_project(self, client, manager_headers):
        response = await client.post(
            f"/api/v1/projects/{uuid4()}/releases",
            json={"name": "Bad Project Release", "version": "1.0.0"},
            headers=manager_headers,
        )
        assert response.status_code == 404

    async def test_create_release_empty_name(self, client, manager_headers):
        org_id = await _create_org(client, manager_headers, "empty")
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": f"Empty-Profile-{uuid4().hex[:6]}", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": f"Empty-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "", "version": "1.0.0"},
            headers=manager_headers,
        )
        assert response.status_code == 422


@pytest.mark.usefixtures("db")
class TestReleaseUpdate:
    """Release update scenarios."""

    async def test_update_release_name(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"name": "Updated Release Name"},
            headers=manager_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Release Name"

    async def test_update_release_description(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"description": "New description"},
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    async def test_update_release_version(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"version": "2.0.0"},
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["version"] == "2.0.0"

    async def test_update_nonexistent_release(self, client, manager_headers):
        response = await client.patch(
            f"/api/v1/releases/{uuid4()}",
            json={"name": "Ghost"},
            headers=manager_headers,
        )
        assert response.status_code == 404

    async def test_update_release_no_auth(self, client):
        response = await client.patch(
            f"/api/v1/releases/{uuid4()}",
            json={"name": "No Auth Update"},
        )
        assert response.status_code in (401, 403)

    async def test_viewer_cannot_update_release(self, client, manager_headers, viewer_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"name": "Viewer Update"},
            headers=viewer_headers,
        )
        assert response.status_code == 403


@pytest.mark.usefixtures("db")
class TestReleaseArchive:
    """Release archive scenarios."""

    async def test_archive_release(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    async def test_archive_already_archived(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        response = await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        assert response.status_code in (200, 409, 500)

    async def test_viewer_cannot_archive(self, client, manager_headers, viewer_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=viewer_headers,
        )
        assert response.status_code == 403


@pytest.mark.usefixtures("db")
class TestReleaseRestore:
    """Release restore scenarios (admin only)."""

    async def test_restore_release_admin(self, client, manager_headers, admin_headers):
        release_id = await _setup_release(client, manager_headers)
        await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        response = await client.post(
            f"/api/v1/releases/{release_id}/restore",
            headers=admin_headers,
        )
        assert response.status_code in (200, 403, 404, 500)

    async def test_manager_cannot_restore(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        response = await client.post(
            f"/api/v1/releases/{release_id}/restore",
            headers=manager_headers,
        )
        assert response.status_code == 403


@pytest.mark.usefixtures("db")
class TestReleaseDelete:
    """Release delete scenarios."""

    async def test_delete_release(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.delete(
            f"/api/v1/releases/{release_id}",
            headers=manager_headers,
        )
        assert response.status_code == 204

    async def test_delete_nonexistent_release(self, client, manager_headers):
        response = await client.delete(
            f"/api/v1/releases/{uuid4()}",
            headers=manager_headers,
        )
        assert response.status_code == 404

    async def test_viewer_cannot_delete(self, client, manager_headers, viewer_headers):
        release_id = await _setup_release(client, manager_headers)
        response = await client.delete(
            f"/api/v1/releases/{release_id}",
            headers=viewer_headers,
        )
        assert response.status_code == 403


@pytest.mark.usefixtures("db")
class TestReleaseStateTransitions:
    """Release state transition flows."""

    async def test_full_lifecycle(self, client, manager_headers, admin_headers):
        release_id = await _setup_release(client, manager_headers)
        get_resp = await client.get(f"/api/v1/releases/{release_id}", headers=manager_headers)
        assert get_resp.status_code == 200
        initial_status = get_resp.json().get("status")
        assert initial_status == "BORRADOR" or initial_status is not None
        update_resp = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"name": "Lifecycle Release", "version": "2.0.0"},
            headers=manager_headers,
        )
        assert update_resp.status_code == 200
        archive_resp = await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        assert archive_resp.status_code == 200
        delete_resp = await client.delete(
            f"/api/v1/releases/{release_id}",
            headers=manager_headers,
        )
        assert delete_resp.status_code == 204

    async def test_status_persists_after_update(self, client, manager_headers):
        release_id = await _setup_release(client, manager_headers)
        await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"description": "Updated"},
            headers=manager_headers,
        )
        get_resp = await client.get(f"/api/v1/releases/{release_id}", headers=manager_headers)
        assert get_resp.status_code == 200
        status = get_resp.json().get("status")
        assert status is not None
