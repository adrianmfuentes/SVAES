"""
Pruebas de Aceptación — Verificación de estructura (ISO 29119-4)

Verifica que los tests Cypress existen y contienen los TC-IDs correctos.
Los tests E2E reales se ejecutan con: npx cypress run --config-file tests/acceptance/cypress.config.js
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

pytestmark = pytest.mark.e2e

ACCEPTANCE_DIR = os.path.dirname(__file__)
SUITE_PATH = os.path.join(ACCEPTANCE_DIR, "cypress", "e2e", "acceptance_suite.cy.js")
COMMANDS_PATH = os.path.join(ACCEPTANCE_DIR, "cypress", "support", "commands.js")
CONFIG_PATH = os.path.join(ACCEPTANCE_DIR, "cypress.config.js")

REQUIRED_TC_IDS = [
    "TC-ACP-CU-00",
    "TC-ACP-CU-01",
    "TC-ACP-CU-02",
    "TC-ACP-CU-03",
    "TC-ACP-UI-01",
    "TC-ACP-FRM-01",
    "TC-ACP-FRM-02",
    "TC-USA-NAV-01",
    "TC-USA-RES-01",
    "TC-USA-SEM-01",
]


def _read_suite():
    if not os.path.exists(SUITE_PATH):
        pytest.skip(f"acceptance_suite.cy.js no encontrado en {SUITE_PATH}")
    with open(SUITE_PATH, encoding="utf-8") as f:
        return f.read()


def test_tc_acp_cu_00_e2e_flow_5_actions():
    """TC-ACP-CU-00: CU-01 base -> VALIDA en <=5 acciones (RNF-19)."""
    content = _read_suite()
    assert "TC-ACP-CU-00" in content, "Falta TC-ACP-CU-00 en suite de aceptación"


def test_tc_acp_cu_01_warning_orange_light():
    """TC-ACP-CU-01: CU-01 RV-04=WARNING -> semáforo naranja."""
    content = _read_suite()
    assert "TC-ACP-CU-01" in content, "Falta TC-ACP-CU-01 en suite de aceptación"


def test_tc_acp_cu_02_error_red_light():
    """TC-ACP-CU-02: CU-01 RV-05=ERROR -> semáforo rojo, msg descriptivo."""
    content = _read_suite()
    assert "TC-ACP-CU-02" in content, "Falta TC-ACP-CU-02 en suite de aceptación"


def test_tc_acp_cu_03_new_user_15min_manual():
    """TC-ACP-CU-03: Usuario nuevo completa flujo en <=15 min (RNF-24) — Manual."""
    content = _read_suite()
    assert "TC-ACP-CU-03" in content, "Falta TC-ACP-CU-03 en suite de aceptación"


def test_tc_acp_ui_01_snapshot_immutable():
    """TC-ACP-UI-01: Snapshot inmutable tras archivar (RNF-36)."""
    content = _read_suite()
    assert "TC-ACP-UI-01" in content, "Falta TC-ACP-UI-01 en suite de aceptación"


def test_tc_acp_frm_01_required_field():
    """TC-ACP-FRM-01: Campo obligatorio vacío -> mensaje campo+acción."""
    content = _read_suite()
    assert "TC-ACP-FRM-01" in content, "Falta TC-ACP-FRM-01 en suite de aceptación"


def test_tc_acp_frm_02_numeric_field_type_error():
    """TC-ACP-FRM-02: Campo numérico con texto -> error de tipo (RNF-20)."""
    content = _read_suite()
    assert "TC-ACP-FRM-02" in content, "Falta TC-ACP-FRM-02 en suite de aceptación"


def test_tc_usa_nav_01_cross_browser():
    """TC-USA-NAV-01: Each choice Chrome/Firefox/Edge/Safari (RNF-29)."""
    content = _read_suite()
    assert "TC-USA-NAV-01" in content, "Falta TC-USA-NAV-01 en suite de aceptación"


def test_tc_usa_res_01_multi_resolution():
    """TC-USA-RES-01: VL resolución 1920/768/375 -> sin desbordamiento (RNF-30)."""
    content = _read_suite()
    assert "TC-USA-RES-01" in content, "Falta TC-USA-RES-01 en suite de aceptación"


def test_tc_usa_sem_01_traffic_light_coherence():
    """TC-USA-SEM-01: Semáforo coherente en dashboard/historial/detalle (RNF-21)."""
    content = _read_suite()
    assert "TC-USA-SEM-01" in content, "Falta TC-USA-SEM-01 en suite de aceptación"


def test_acceptance_suite_file_exists():
    """Verifica que los archivos de la suite de aceptación existen."""
    assert os.path.exists(SUITE_PATH), f"No existe {SUITE_PATH}"
    assert os.path.exists(COMMANDS_PATH), f"No existe {COMMANDS_PATH}"
    assert os.path.exists(CONFIG_PATH), f"No existe {CONFIG_PATH}"


def test_all_required_tc_ids_present():
    """Verifica que los 10 TC-IDs de aceptación están en la suite."""
    content = _read_suite()
    missing = [tc_id for tc_id in REQUIRED_TC_IDS if tc_id not in content]
    assert not missing, f"Faltan TC-IDs en la suite de aceptación: {missing}"
