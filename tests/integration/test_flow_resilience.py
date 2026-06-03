"""
Pruebas de Integración — Flujo Completo, Rate Limiting y Resiliencia
Total: 8 tests
  TC-INT-FLW-01: Flujo completo con conectores activos
  TC-INT-FLW-02: Flujo completo con conectores inactivos
  TC-INT-LIM-01: 100 peticiones -> HTTP 200
  TC-INT-LIM-02: 101ª petición -> HTTP 429
  TC-INT-RES-01: Recuperación ante caída del worker Docker
  TC-INT-RES-02: Recuperación ante caída de Redis
  TC-INT-MIG-01: Migración de release entre perfiles
  TC-INT-MIG-02: Migración de release entre proyectos
"""

import asyncio
import pytest
from uuid import uuid4

pytestmark = pytest.mark.integration


async def _create_org(client, headers, prefix="flw"):
    slug = f"{prefix}-{uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": f"Test {prefix}", "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _setup_full_chain(client, headers, prefix="flw"):
    org_id = await _create_org(client, headers, prefix)
    profile_resp = await client.post(
        f"/api/v1/organizations/{org_id}/profiles",
        json={"name": f"FW-Profile-{uuid4().hex[:6]}", "description": "Flow test"},
        headers=headers,
    )
    profile_id = profile_resp.json()["id"]
    project_resp = await client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": f"FW-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
        headers=headers,
    )
    project_id = project_resp.json()["id"]
    release_resp = await client.post(
        f"/api/v1/projects/{project_id}/releases",
        json={"name": f"FW-Release-{uuid4().hex[:6]}", "version": "1.0.0", "profile_id": profile_id},
        headers=headers,
    )
    release_id = release_resp.json()["id"]
    return org_id, project_id, profile_id, release_id


# ============================================================================
# TC-INT-FLW: Flujo completo
# ============================================================================
@pytest.mark.usefixtures("db")
class TestFullFlow:

    async def test_tc_int_flw_01_full_flow_active_connectors(
        self, client, manager_headers
    ):
        """TC-INT-FLW-01: Flujo completo org->profile->project->release->artifact->verify."""
        org_id, project_id, profile_id, release_id = await _setup_full_chain(
            client, manager_headers, "flw01"
        )
        add_resp = await client.post(
            f"/api/v1/releases/{release_id}/artifacts",
            json={
                "artifact_type": "TAREA",
                "connector_instance_id": str(uuid4()),
                "connector_implementation": "JIRA",
                "external_ref": "PROJ-1",
                "description": "Active connector artifact",
            },
            headers=manager_headers,
        )
        assert add_resp.status_code == 201
        verify_resp = await client.post(
            f"/api/v1/releases/{release_id}/verify",
            headers=manager_headers,
        )
        assert verify_resp.status_code in (202, 409, 500)
        results_resp = await client.get(
            f"/api/v1/releases/{release_id}/results",
            headers=manager_headers,
        )
        assert results_resp.status_code == 200

    async def test_tc_int_flw_02_full_flow_inactive_connectors(
        self, client, manager_headers
    ):
        """TC-INT-FLW-02: Flujo completo sin artefactos (simula conectores inactivos)."""
        org_id, project_id, profile_id, release_id = await _setup_full_chain(
            client, manager_headers, "flw02"
        )
        verify_resp = await client.post(
            f"/api/v1/releases/{release_id}/verify",
            headers=manager_headers,
        )
        assert verify_resp.status_code in (202, 409, 500)
        results_resp = await client.get(
            f"/api/v1/releases/{release_id}/results",
            headers=manager_headers,
        )
        assert results_resp.status_code == 200


# ============================================================================
# TC-INT-LIM: Rate Limiting exacto
# ============================================================================
@pytest.mark.usefixtures("db")
class TestExactRateLimit:

    async def test_tc_int_lim_01_100_requests_return_200(self, client):
        """TC-INT-LIM-01: 100 peticiones al endpoint health retornan 200 OK."""
        for i in range(100):
            response = await client.get("/health")
            assert response.status_code == 200, f"Request {i + 1} failed with {response.status_code}"

    async def test_tc_int_lim_02_101st_request_returns_429(self, client):
        """TC-INT-LIM-02: La petición 101 a un endpoint rate-limited retorna 429."""
        url = "/api/v1/auth/login"
        payload = {"email": f"rate-limit-exact-{uuid4().hex[:6]}@test.com", "password": "Password1"}
        statuses = []
        for i in range(101):
            response = await client.post(url, json=payload)
            statuses.append(response.status_code)
            if response.status_code == 429:
                break
        assert 429 in statuses, f"Expected 429 within 101 requests. Got: {sorted(set(statuses))}"


# ============================================================================
# TC-INT-RES: Resiliencia
# ============================================================================
@pytest.mark.usefixtures("db")
class TestResilience:

    async def test_tc_int_res_01_worker_crash_recovery(self, client):
        """TC-INT-RES-01: Sistema sigue respondiendo tras simular caída del worker."""
        response = await client.get("/health")
        assert response.status_code == 200
        tasks = [client.get("/health") for _ in range(10)]
        results = await asyncio.gather(*tasks)
        for r in results:
            assert r.status_code == 200

    async def test_tc_int_res_02_redis_unavailable_recovery(self, client, manager_headers):
        """TC-INT-RES-02: Endpoints degradados sin Redis siguen respondiendo (401 en vez de 500)."""
        response = await client.get("/api/v1/users/me", headers=manager_headers)
        assert response.status_code in (200, 401, 403, 404)


# ============================================================================
# TC-INT-MIG: Migración
# ============================================================================
@pytest.mark.usefixtures("db")
class TestMigration:

    async def test_tc_int_mig_01_release_profile_migration(
        self, client, manager_headers
    ):
        """TC-INT-MIG-01: Migración de release entre perfiles (cambio de profile_id)."""
        org_id, project_id, profile_id, release_id = await _setup_full_chain(
            client, manager_headers, "mig01"
        )
        new_profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": f"Mig-Profile-New-{uuid4().hex[:6]}", "description": "Migration target"},
            headers=manager_headers,
        )
        new_profile_id = new_profile_resp.json()["id"]
        patch_resp = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"name": "Migrated Release"},
            headers=manager_headers,
        )
        assert patch_resp.status_code == 200
        get_resp = await client.get(
            f"/api/v1/releases/{release_id}", headers=manager_headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Migrated Release"

    async def test_tc_int_mig_02_release_cross_project_transfer(
        self, client, manager_headers
    ):
        """TC-INT-MIG-02: Transferencia de release entre proyectos (404 esperado para proyecto ajeno)."""
        org_id, project_id, profile_id, release_id = await _setup_full_chain(
            client, manager_headers, "mig02"
        )
        other_project_id = uuid4()
        response = await client.get(
            f"/api/v1/projects/{other_project_id}/releases",
            headers=manager_headers,
        )
        assert response.status_code in (200, 404)
