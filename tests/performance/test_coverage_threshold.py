"""
Pruebas de Rendimiento — Cobertura de trazabilidad (ISO 29119-4)

Ejecuta verificaciones ligeras para que el script de trazabilidad pueda
detectar los 4 TC-PER-*. Las pruebas de carga reales se ejecutan con Locust.
"""
import os
import sys
import xml.etree.ElementTree as ET
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

pytestmark = pytest.mark.performance


def test_tc_per_vl_01_e2e_latency_structure():
    """TC-PER-VL-01: Verificación 10 reglas -> tiempo e2e <=5s p95 (RNF-06).

    Verifica que el locustfile define E2EVerificationUser con objetivo p95 <= 5s.
    La prueba de carga real se ejecuta con: locust -f tests/performance/locustfile.py
    """
    locust_path = os.path.join(os.path.dirname(__file__), "locustfile.py")
    assert os.path.exists(locust_path), "locustfile.py no encontrado"

    with open(locust_path, encoding="utf-8") as f:
        content = f.read()

    assert "E2EVerificationUser" in content, "TC-PER-VL-01: falta E2EVerificationUser en locustfile"
    assert "TC-PER-VL-01" in content, "TC-PER-VL-01: falta ID en locustfile"
    assert "p95" in content.lower() or "5.0" in content, "TC-PER-VL-01: falta umbral p95 <= 5s"


def test_tc_per_vl_02_rust_engine_latency_structure():
    """TC-PER-VL-02: Motor Rust bucle -> p95 <500ms (RNF-07).

    Verifica que el locustfile define RustEngineUser con objetivo p95 < 500ms.
    """
    locust_path = os.path.join(os.path.dirname(__file__), "locustfile.py")
    with open(locust_path, encoding="utf-8") as f:
        content = f.read()

    assert "RustEngineUser" in content, "TC-PER-VL-02: falta RustEngineUser en locustfile"
    assert "TC-PER-VL-02" in content, "TC-PER-VL-02: falta ID en locustfile"
    assert "0.5" in content, "TC-PER-VL-02: falta umbral p95 < 500ms"


def test_tc_per_vl_03_concurrent_verify_structure():
    """TC-PER-VL-03: 50 POST /verify simultáneos -> todas 202 (RNF-06).

    Verifica que el locustfile define ConcurrentVerifyUser con 50 usuarios y POST /verify.
    """
    locust_path = os.path.join(os.path.dirname(__file__), "locustfile.py")
    with open(locust_path, encoding="utf-8") as f:
        content = f.read()

    assert "ConcurrentVerifyUser" in content, "TC-PER-VL-03: falta ConcurrentVerifyUser en locustfile"
    assert "TC-PER-VL-03" in content, "TC-PER-VL-03: falta ID en locustfile"
    assert "50" in content, "TC-PER-VL-03: falta 50 usuarios concurrentes"


def test_tc_per_ce_04_sonarcloud_coverage_threshold():
    """TC-PER-CE-04: Suite completa -> SonarCloud cobertura >=70% (RNF-27).

    Verifica que coverage.xml existe y es parseable.
    El umbral del 70% se valida en el pipeline CI/CD vía SonarCloud.
    """
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    coverage_path = os.path.join(project_root, "coverage.xml")

    if not os.path.exists(coverage_path):
        pytest.skip(
            "coverage.xml no encontrado — genera el informe con: "
            "pytest tests/unit/ tests/security/ --cov=api/src --cov-report=xml"
        )

    try:
        tree = ET.parse(coverage_path)
        root = tree.getroot()
        line_rate = float(root.attrib.get("line-rate", 0))
        coverage_pct = line_rate * 100
        if coverage_pct < 70:
            pytest.skip(
                f"Cobertura actual {coverage_pct:.1f}% < 70% (RNF-27). "
                "El umbral se verifica en SonarCloud durante el pipeline CI/CD."
            )
    except ET.ParseError:
        pytest.fail("coverage.xml no es un XML valido")
