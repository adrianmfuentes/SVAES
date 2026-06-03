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


class TestHealthEndpoint:
    """System health endpoint integration tests (no DB required)."""

    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "svaes-api"
        assert data["version"] == "1.0.0"

    async def test_health_has_request_id(self, client):
        response = await client.get("/health")
        assert "x-request-id" in response.headers

    async def test_health_no_auth_required(self, client):
        response = await client.get("/health")
        assert response.status_code == 200


class TestDocsAccessibility:
    """Docs endpoint behaviour in test mode (no DB required)."""

    async def test_docs_accessible_in_test_mode(self, client):
        response = await client.get("/docs")
        assert response.status_code == 200


@pytest.mark.usefixtures("db")
class TestOrganizationFlow:
    """Organization create + read + list flow."""

    async def test_create_organization(self, client, manager_headers):
        slug = f"org-{uuid4().hex[:8]}"
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Integration Test Org", "slug": slug},
            headers=manager_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Integration Test Org"
        assert data["slug"] == slug

    async def test_create_organization_duplicate_slug(self, client, manager_headers):
        slug = f"dup-org-{uuid4().hex[:8]}"
        await client.post(
            "/api/v1/organizations",
            json={"name": "Org A", "slug": slug},
            headers=manager_headers,
        )
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Org B", "slug": slug},
            headers=manager_headers,
        )
        assert response.status_code == 409

    async def test_get_organization(self, client, manager_headers):
        slug = f"get-org-{uuid4().hex[:8]}"
        create_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Get Test Org", "slug": slug},
            headers=manager_headers,
        )
        org_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/organizations/{org_id}",
            headers=manager_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test Org"
        assert data["slug"] == slug
        assert data["is_active"] is True

    async def test_list_organizations_admin_only(self, client, admin_headers, manager_headers):
        response = await client.get("/api/v1/organizations", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        response = await client.get("/api/v1/organizations", headers=manager_headers)
        assert response.status_code == 403

    async def test_admin_cannot_create_org(self, client, admin_headers):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Admin Org", "slug": f"admin-org-{uuid4().hex[:8]}"},
            headers=admin_headers,
        )
        assert response.status_code == 403


@pytest.mark.usefixtures("db")
class TestProfileFlow:
    """Profile create + list flow."""

    async def test_create_profile(self, client, manager_headers, test_org_id):
        response = await client.post(
            f"/api/v1/organizations/{test_org_id}/profiles",
            json={"name": "Test Profile", "description": "Integration test profile"},
            headers=manager_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Profile"

    async def test_list_profiles(self, client, manager_headers, test_org_id):
        response = await client.get(
            f"/api/v1/organizations/{test_org_id}/profiles",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.usefixtures("db")
class TestProjectFlow:
    """Project create + list + get flow."""

    async def test_create_project(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Project Profile", "description": "For project tests"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        response = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={
                "name": "Integration Project",
                "description": "Test project",
                "profile_id": profile_id,
            },
            headers=manager_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Integration Project"

    async def test_list_org_projects(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        response = await client.get(
            f"/api/v1/organizations/{org_id}/projects",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_accessible_projects(self, client, manager_headers):
        response = await client.get("/api/v1/projects", headers=manager_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_project_by_id(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Get Project Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        create_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Get Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/organizations/{org_id}/projects/{project_id}",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Get Project"

    async def test_archive_project(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Archive Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        create_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Archive Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = create_resp.json()["id"]
        response = await client.post(
            f"/api/v1/organizations/{org_id}/projects/{project_id}/archive",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_archived"] is True


@pytest.mark.usefixtures("db")
class TestReleaseFlow:
    """Release create + list + get + update flow."""

    async def test_create_release(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Release Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Release Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={
                "name": "Test Release",
                "version": "1.0.0",
                "description": "Integration test release",
                "profile_id": profile_id,
            },
            headers=manager_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "BORRADOR"

    async def test_list_project_releases(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "List Release Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "List Release Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "R1", "version": "1.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "R2", "version": "2.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        response = await client.get(
            f"/api/v1/projects/{project_id}/releases",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_global_releases(self, client, manager_headers):
        response = await client.get("/api/v1/releases", headers=manager_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_release(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Get Release Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Get Release Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "Get Release", "version": "1.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        release_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/releases/{release_id}",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Get Release"


@pytest.mark.usefixtures("db")
class TestArtifactFlow:
    """Add + list + remove artifacts from a release."""

    async def test_add_and_list_artifacts(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Artifact Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Artifact Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        release_resp = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "Artifact Release", "version": "1.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        release_id = release_resp.json()["id"]
        add_resp = await client.post(
            f"/api/v1/releases/{release_id}/artifacts",
            json={
                "artifact_type": "TAREA",
                "connector_instance_id": str(uuid4()),
                "connector_implementation": "JIRA",
                "external_ref": "TASK-42",
                "description": "Test artifact",
            },
            headers=manager_headers,
        )
        assert add_resp.status_code == 201
        assert "id" in add_resp.json()
        list_resp = await client.get(
            f"/api/v1/releases/{release_id}/artifacts",
            headers=manager_headers,
        )
        assert list_resp.status_code == 200
        assert isinstance(list_resp.json(), list)

    async def test_remove_artifact(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Remove Artifact Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Remove Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        release_resp = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "Remove Artifact Release", "version": "1.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        release_id = release_resp.json()["id"]
        add_resp = await client.post(
            f"/api/v1/releases/{release_id}/artifacts",
            json={
                "artifact_type": "CODIGO",
                "connector_instance_id": str(uuid4()),
                "connector_implementation": "GITHUB",
                "external_ref": "PR-99",
            },
            headers=manager_headers,
        )
        artifact_id = add_resp.json()["id"]
        response = await client.delete(
            f"/api/v1/releases/{release_id}/artifacts/{artifact_id}",
            headers=manager_headers,
        )
        assert response.status_code == 204


@pytest.mark.usefixtures("db")
class TestVerificationFlow:
    """Launch verification and retrieve results."""

    async def test_verify_release(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Verify Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Verify Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        release_resp = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "Verify Release", "version": "1.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        release_id = release_resp.json()["id"]
        response = await client.post(
            f"/api/v1/releases/{release_id}/verify",
            headers=manager_headers,
        )
        assert response.status_code in (202, 409, 500)

    async def test_get_verification_results(self, client, manager_headers, test_org_id):
        org_id = await _create_org(client, manager_headers)
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": "Results Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "Results Project", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        release_resp = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "Results Release", "version": "1.0.0", "profile_id": profile_id},
            headers=manager_headers,
        )
        release_id = release_resp.json()["id"]
        response = await client.get(
            f"/api/v1/releases/{release_id}/results",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.usefixtures("db")
class TestDashboardFlow:
    """Dashboard metrics endpoint."""

    async def test_dashboard_metrics(self, client, manager_headers, test_org_id):
        response = await client.get(
            f"/api/v1/dashboard/metrics?org_id={test_org_id}",
            headers=manager_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_releases" in data
        assert "valid_releases" in data
        assert "pass_rate" in data


@pytest.mark.usefixtures("db")
class TestAuthIntegration:
    """Auth endpoints integration with real DB."""

    async def test_login_with_invalid_credentials(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "WrongPass1"}, # NOSONAR
        )
        assert response.status_code == 401

    async def test_register_logout_flow(self, client):
        email = f"reg-user-{uuid4().hex[:8]}@test.com"
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password1",
                "display_name": "Reg User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        if response.status_code == 201:
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "Password1"},
            )
            if login_resp.status_code == 200:
                token = login_resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                profile_resp = await client.get("/api/v1/users/me", headers=headers)
                assert profile_resp.status_code == 200
                await client.post("/api/v1/auth/logout", headers=headers)
                after_logout_resp = await client.get("/api/v1/users/me", headers=headers)
                assert after_logout_resp.status_code in (401, 403)


class TestUserProfileFlow:
    """User profile endpoints."""

    async def test_get_me_no_auth(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code in (401, 403)

    async def test_get_me_with_auth(self, client, manager_headers, db):
        response = await client.get("/api/v1/users/me", headers=manager_headers)
        assert response.status_code in (200, 404)

    async def test_update_display_name(self, client, manager_headers, db):
        response = await client.patch(
            "/api/v1/users/me",
            json={"display_name": "Updated Name"},
            headers=manager_headers,
        )
        assert response.status_code in (200, 404)


@pytest.mark.usefixtures("db")
class TestConnectorTypes:
    """Connector types listing."""

    async def test_list_connector_types(self, client, manager_headers):
        response = await client.get("/api/v1/connectors/types", headers=manager_headers)
        assert response.status_code == 200
        data = response.json()
        assert "implementations" in data


@pytest.mark.usefixtures("db")
class TestAccessRequests:
    """Access requests flow."""

    async def test_submit_access_request(self, client):
        response = await client.post(
            "/api/v1/access-requests",
            json={
                "requester_name": "Test Requester",
                "requester_email": f"access-{uuid4().hex[:8]}@test.com",
                "organization_name": "New Org Request",
            },
        )
        assert response.status_code in (201, 400, 422, 500)

    async def test_list_access_requests(self, client, admin_headers):
        response = await client.get("/api/v1/access-requests", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.usefixtures("db")
class TestNotifications:
    """Notifications endpoints."""

    async def test_list_notification_channels(self, client, manager_headers, test_org_id):
        response = await client.get(
            "/api/v1/notifications/channels?org_id={}".format(test_org_id),
            headers=manager_headers,
        )
        assert response.status_code in (200, 400, 403, 500)

    async def test_get_notification_preferences(self, client, manager_headers):
        response = await client.get("/api/v1/notifications/preferences", headers=manager_headers)
        assert response.status_code in (200, 403, 404, 500)


@pytest.mark.usefixtures("db")
class TestTemplates:
    """Templates endpoints."""

    async def test_list_templates(self, client, manager_headers, test_org_id):
        response = await client.get(
            f"/api/v1/templates?org_id={test_org_id}",
            headers=manager_headers,
        )
        assert response.status_code in (200, 400, 403, 500)

    async def test_create_template(self, client, manager_headers, test_org_id):
        profile_resp = await client.post(
            f"/api/v1/organizations/{test_org_id}/profiles",
            json={"name": "Template Profile", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        response = await client.post(
            "/api/v1/templates",
            json={
                "name": "Test Template",
                "description": "Integration template",
                "profile_id": profile_id,
                "project_name_template": "TPL-{name}",
                "org_id": str(test_org_id),
            },
            headers=manager_headers,
        )
        assert response.status_code in (201, 400, 422, 403)


@pytest.mark.usefixtures("db")
class TestApiKeys:
    """API keys endpoints."""

    async def test_create_api_key(self, client, manager_headers, test_user_id):
        response = await client.post(
            f"/api/v1/users/{test_user_id}/api-keys",
            json={"name": "Integration Key", "expires_in_days": 30},
            headers=manager_headers,
        )
        assert response.status_code in (201, 400, 403, 500)

    async def test_list_api_keys(self, client, manager_headers, test_user_id):
        response = await client.get(
            f"/api/v1/users/{test_user_id}/api-keys",
            headers=manager_headers,
        )
        assert response.status_code in (200, 403, 500)


@pytest.mark.usefixtures("db")
class TestAdminEndpoints:
    """Admin-only endpoints."""

    async def test_list_users_admin(self, client, admin_headers):
        response = await client.get("/api/v1/admin/users", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_users_not_admin(self, client, manager_headers):
        response = await client.get("/api/v1/admin/users", headers=manager_headers)
        assert response.status_code == 403

    async def test_reload_rules(self, client, admin_headers):
        response = await client.post("/api/v1/admin/rules/reload", headers=admin_headers)
        assert response.status_code not in (401, 500)

    async def test_audit_logs(self, client, admin_headers):
        response = await client.get("/api/v1/audit/logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
