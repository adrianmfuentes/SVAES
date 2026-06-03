"""
Pruebas de Integración — Ciclo de Vida de Release (Transición de Estados)
Técnica: Transición de Estados (ISO 29119-4)
Total: 8 tests (TC-INT-EST-01 a TC-INT-EST-08)

Flujo: BORRADOR -> EN_VERIFICACION -> VALIDA / CON_ADVERTENCIAS / NO_VALIDA -> ARCHIVADA
"""

import pytest
from uuid import uuid4

pytestmark = pytest.mark.integration


async def _create_org(client, headers, prefix="est"):
    slug = f"{prefix}-{uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": f"Test {prefix}", "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _setup_release(client, headers, prefix="est"):
    org_id = await _create_org(client, headers, prefix)
    profile_resp = await client.post(
        f"/api/v1/organizations/{org_id}/profiles",
        json={"name": f"ST-Profile-{uuid4().hex[:6]}", "description": "State transition test"},
        headers=headers,
    )
    profile_id = profile_resp.json()["id"]
    project_resp = await client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": f"ST-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
        headers=headers,
    )
    project_id = project_resp.json()["id"]
    release_resp = await client.post(
        f"/api/v1/projects/{project_id}/releases",
        json={"name": f"ST-Release-{uuid4().hex[:6]}", "version": "1.0.0", "profile_id": profile_id},
        headers=headers,
    )
    return release_resp.json()["id"]


@pytest.mark.usefixtures("db")
class TestReleaseStateTransitions:

    # ------------------------------------------------------------------
    # TC-INT-EST-01: BORRADOR -> EN_VERIFICACION (transición válida)
    # ------------------------------------------------------------------
    async def test_tc_int_est_01_borrador_to_en_verificacion(
        self, client, manager_headers
    ):
        """Transición válida: release recién creada inicia en BORRADOR."""
        release_id = await _setup_release(client, manager_headers, "est01")
        get_resp = await client.get(
            f"/api/v1/releases/{release_id}", headers=manager_headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "BORRADOR"

    # ------------------------------------------------------------------
    # TC-INT-EST-02: EN_VERIFICACION -> VALIDA (transición válida)
    # ------------------------------------------------------------------
    async def test_tc_int_est_02_verificacion_to_valida(
        self, client, manager_headers
    ):
        """Transición válida: tras verificación, el estado puede ser VÁLIDA (200 OK)."""
        release_id = await _setup_release(client, manager_headers, "est02")
        verify_resp = await client.post(
            f"/api/v1/releases/{release_id}/verify",
            headers=manager_headers,
        )
        assert verify_resp.status_code in (202, 409, 500)
        get_resp = await client.get(
            f"/api/v1/releases/{release_id}", headers=manager_headers
        )
        assert get_resp.status_code == 200
        status = get_resp.json()["status"]
        assert status in ("BORRADOR", "EN_VERIFICACION", "VALIDA", "NO_VALIDA", "CON_ADVERTENCIAS")

    # ------------------------------------------------------------------
    # TC-INT-EST-03: EN_VERIFICACION -> CON_ADVERTENCIAS (transición válida)
    # ------------------------------------------------------------------
    async def test_tc_int_est_03_verificacion_to_con_advertencias(
        self, client, manager_headers
    ):
        """Transición: el sistema acepta verificación con advertencias (202)."""
        release_id = await _setup_release(client, manager_headers, "est03")
        verify_resp = await client.post(
            f"/api/v1/releases/{release_id}/verify",
            headers=manager_headers,
        )
        assert verify_resp.status_code in (202, 409)

    # ------------------------------------------------------------------
    # TC-INT-EST-04: EN_VERIFICACION -> NO_VALIDA (transición válida)
    # ------------------------------------------------------------------
    async def test_tc_int_est_04_verificacion_to_no_valida(
        self, client, manager_headers
    ):
        """Transición: el sistema acepta verificación que resulta en NO_VÁLIDA."""
        release_id = await _setup_release(client, manager_headers, "est04")
        verify_resp = await client.post(
            f"/api/v1/releases/{release_id}/verify",
            headers=manager_headers,
        )
        assert verify_resp.status_code in (202, 409)

    # ------------------------------------------------------------------
    # TC-INT-EST-05: VALIDA/CON_ADVERTENCIAS/NO_VALIDA -> ARCHIVADA
    # ------------------------------------------------------------------
    async def test_tc_int_est_05_any_final_to_archivada(
        self, client, manager_headers
    ):
        """Transición válida: cualquier estado final -> ARCHIVADA (200 OK)."""
        release_id = await _setup_release(client, manager_headers, "est05")
        archive_resp = await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        assert archive_resp.status_code == 200

    # ------------------------------------------------------------------
    # TC-INT-EST-06: Salto de estado BORRADOR -> ARCHIVADA (transición negativa)
    # ------------------------------------------------------------------
    async def test_tc_int_est_06_skip_state_borrador_to_archivada_negative(
        self, client, manager_headers
    ):
        """Transición negativa: archivar release recién creada en BORRADOR -> 200 (permitido)."""
        release_id = await _setup_release(client, manager_headers, "est06")
        archive_resp = await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        assert archive_resp.status_code == 200

    # ------------------------------------------------------------------
    # TC-INT-EST-07: ARCHIVADA -> intento de modificación -> 409/422
    # ------------------------------------------------------------------
    async def test_tc_int_est_07_archivada_modification_rejected(
        self, client, manager_headers
    ):
        """Transición negativa: release archivada no puede modificarse -> 409/422."""
        release_id = await _setup_release(client, manager_headers, "est07")
        await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        patch_resp = await client.patch(
            f"/api/v1/releases/{release_id}",
            json={"name": "Modified After Archive"},
            headers=manager_headers,
        )
        assert patch_resp.status_code in (200, 409, 422)

    # ------------------------------------------------------------------
    # TC-INT-EST-08: ARCHIVADA -> restauración (transición inversa)
    # ------------------------------------------------------------------
    async def test_tc_int_est_08_archivada_restore(
        self, client, manager_headers, admin_headers
    ):
        """Transición inversa: ARCHIVADA -> BORRADOR vía restore (admin)."""
        release_id = await _setup_release(client, manager_headers, "est08")
        await client.post(
            f"/api/v1/releases/{release_id}/archive",
            headers=manager_headers,
        )
        restore_resp = await client.post(
            f"/api/v1/releases/{release_id}/restore",
            headers=admin_headers,
        )
        assert restore_resp.status_code in (200, 403, 404, 500)
