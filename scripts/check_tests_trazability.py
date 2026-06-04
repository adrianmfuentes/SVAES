#!/usr/bin/env python3
"""
check_traceability.py — Verificación de trazabilidad entre el plan de pruebas
del SVAES (77 casos) y los tests implementados.

Uso:
    python check_traceability.py [archivo1] [archivo2] ...

Los archivos pueden ser de cualquiera de estos formatos (se detectan automáticamente):
  · pytest -v          →  "PASSED tests/...::test_TC_UNI_AGG_01_..."
  · cargo test         →  "test tc_uni_mot_01_rv01 ... ok"
  · jest --verbose     →  "✓ TC-UNI-FE-GRD-01 token válido ..."
  · JUnit XML          →  pytest --junit-xml=report.xml  /  jest --reporters=jest-junit
  · stdin              →  sin argumentos, lee de stdin

Salidas generadas (en tests/results):
   · Resumen en consola con colores ANSI
   · traceability_report.md   → tabla Markdown lista para copiar en la memoria
   · traceability_report.csv  → para importar en Excel/Sheets

Convención de nombres recomendada:
  pytest  → def test_TC_UNI_AGG_01_descripcion():
  cargo   → fn tc_uni_mot_01_descripcion() { }
  jest    → it('TC-UNI-FE-GRD-01 descripcion', ...)

El script también detecta los IDs aunque lleven guiones bajos en lugar de guiones
(TC_UNI_AGG_01 == TC-UNI-AGG-01).

Código de salida:
  0 → todos los casos del plan están cubiertos y pasan
  1 → hay casos sin implementar o con fallo
"""

from __future__ import annotations
import re
import sys
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO COMPLETO DEL PLAN DE PRUEBAS (77 casos)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlanEntry:
    tc_id: str
    level: str        # Unitaria | Integración | Aceptación | Rendimiento | Seguridad
    section: str      # §7.2.x, §7.3.x, etc.
    description: str
    technique: str    # CE+VL | Each Choice | Base Choice | TE | CE | BC
    tool: str         # pytest | cargo test | Jest | Manual+Cypress | Locust | OWASP ZAP

SECTION_7_2_1 = "§7.2.1"
SECTION_7_2_2 = "§7.2.2"
SECTION_7_2_3 = "§7.2.3"
SECTION_7_2_4 = "§7.2.4"
SECTION_7_2_5_1 = "§7.2.5.1"
SECTION_7_2_5_2 = "§7.2.5.2"
SECTION_7_2_5_3 = "§7.2.5.3"
SECTION_7_3_1 = "§7.3.1"
SECTION_7_3_2 = "§7.3.2"
SECTION_7_4 = "§7.4"
SECTION_7_5 = "§7.5"
SECTION_7_6 = "§7.6"
LEVEL_UNITARIA = "Unitaria"
LEVEL_INTEGRACION = "Integración"
LEVEL_ACEPTACION = "Aceptación"
LEVEL_RENDIMIENTO = "Rendimiento"
LEVEL_SEGURIDAD = "Seguridad"
TECH_CE_VL = "CE+VL"
TECH_EACH_CHOICE = "Each Choice"
TECH_BASE_CHOICE = "Base Choice"
TECH_CE_BC = "CE+BC"
TECH_CE = "CE"
TECH_TE = "TE"
TECH_VL = "VL"
TOOL_CARGO_TEST = "cargo test"
TOOL_PYTEST = "pytest"
TOOL_JEST = "Jest"
TOOL_PYTEST_DOCKER = "pytest+Docker"
TOOL_MANUAL_CYPRESS = "Manual+Cypress"
TOOL_MANUAL = "Manual"
TOOL_CYPRESS = "Cypress"
TOOL_LOCUST = "Locust"
TOOL_SONARCLOUD = "SonarCloud"

PLAN: list[PlanEntry] = [
    # ── §7.2.1 Aggregator ──────────────────────────────────────────────────
    PlanEntry("TC-UNI-AGG-01", LEVEL_UNITARIA, SECTION_7_2_1,
              "Todas OBL=OK, OPC=OK → VALID",                  TECH_CE_VL, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-AGG-02", LEVEL_UNITARIA, SECTION_7_2_1,
              "≥1 OBL=ERROR → INVALID",                        TECH_CE_VL, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-AGG-03", LEVEL_UNITARIA, SECTION_7_2_1,
              "OBL todas OK, ≥1 OPC=WARNING → VALID_WITH_WARNINGS", TECH_CE_VL, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-AGG-04", LEVEL_UNITARIA, SECTION_7_2_1,
              "VL: 0 reglas OBL con ERROR → veredicto≠INVALID", TECH_CE_VL, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-AGG-05", LEVEL_UNITARIA, SECTION_7_2_1,
              "VL: 1 regla OBL con ERROR → INVALID",           TECH_CE_VL, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-AGG-06", LEVEL_UNITARIA, SECTION_7_2_1,
              "VL: 1 NOT_EVALUATED → sufijo _WITH_INCIDENTS",  TECH_CE_VL, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-AGG-07", LEVEL_UNITARIA, SECTION_7_2_1,
              "VL: 0 NOT_EVALUATED → sin sufijo",              TECH_CE_VL, TOOL_CARGO_TEST),

    # ── §7.2.2 Catálogo reglas RV-01..RV-10 ───────────────────────────────
    PlanEntry("TC-UNI-MOT-01", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-01 Conector ACTIVO, artefacto OK",           TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-02", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-01 Conector INACTIVO → NOT_EVALUATED",       TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-03", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-02 ID cruzado válido",                       TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-04", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-02 ID en commit NOT_FOUND en Jira → ERROR",  TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-05", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-03 Cobertura documental completa",           TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-06", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-04 Versión coherente",                       TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-07", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-05 Tarea bloqueante → ERROR",                TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-08", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-06 Campo obligatorio vacío → ERROR",         TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-09", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-07 Back-reference válida",                   TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-10", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-08 Artefacto con antigüedad > umbral → WARNING", TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-11", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-09 Dos artefactos mismo external_id → ERROR",TECH_EACH_CHOICE, TOOL_CARGO_TEST),
    PlanEntry("TC-UNI-MOT-12", LEVEL_UNITARIA, SECTION_7_2_2,
              "RV-10 Documento aprobado existe",               TECH_EACH_CHOICE, TOOL_CARGO_TEST),

    # ── §7.2.3 Endpoints FastAPI ───────────────────────────────────────────
    PlanEntry("TC-UNI-API-00", LEVEL_UNITARIA, SECTION_7_2_3,
              "Base OPERATOR+válido+propia+completo → 201",    TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-01", LEVEL_UNITARIA, SECTION_7_2_3,
              "rol=ADMIN → 201",                               TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-02", LEVEL_UNITARIA, SECTION_7_2_3,
              "rol=VIEWER → 403",                              TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-03", LEVEL_UNITARIA, SECTION_7_2_3,
              "autenticación=token_caducado → 401",            TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-04", LEVEL_UNITARIA, SECTION_7_2_3,
              "autenticación=sin_token → 401",                 TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-05", LEVEL_UNITARIA, SECTION_7_2_3,
              "org_context=ajena → 404",                       TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-06", LEVEL_UNITARIA, SECTION_7_2_3,
              "body campo faltante → 422",                     TECH_BASE_CHOICE, TOOL_PYTEST),
    PlanEntry("TC-UNI-API-07", LEVEL_UNITARIA, SECTION_7_2_3,
              "body tipo incorrecto → 422",                    TECH_BASE_CHOICE, TOOL_PYTEST),

    # ── §7.2.4 IConnector ─────────────────────────────────────────────────
    PlanEntry("TC-UNI-CON-01", LEVEL_UNITARIA, SECTION_7_2_4,
              "Credenciales OK, URL alcanzable → ACTIVO",      TECH_CE_VL, TOOL_PYTEST),
    PlanEntry("TC-UNI-CON-02", LEVEL_UNITARIA, SECTION_7_2_4,
              "Token caducado → AuthError / INACTIVO",         TECH_CE_VL, TOOL_PYTEST),
    PlanEntry("TC-UNI-CON-03", LEVEL_UNITARIA, SECTION_7_2_4,
              "URL inexistente → ConnectionError / INACTIVO",  TECH_CE_VL, TOOL_PYTEST),
    PlanEntry("TC-UNI-CON-04", LEVEL_UNITARIA, SECTION_7_2_4,
              "VL latencia = timeout exacto → TimeoutError",   TECH_CE_VL, TOOL_PYTEST),
    PlanEntry("TC-UNI-CON-05", LEVEL_UNITARIA, SECTION_7_2_4,
              "VL latencia = timeout−1 ms → OK",               TECH_CE_VL, TOOL_PYTEST),
    PlanEntry("TC-UNI-CON-06", LEVEL_UNITARIA, SECTION_7_2_4,
              "Conector INACTIVO en verificación → sin HTTP",  TECH_CE_VL, TOOL_PYTEST),

    # ── §7.2.5.1 Guards Angular ───────────────────────────────────────────
    PlanEntry("TC-UNI-FE-GRD-01", LEVEL_UNITARIA, SECTION_7_2_5_1,
              "Token válido, U2/OPERATOR, ruta permitida → canActivate=true", TECH_CE_BC, TOOL_JEST),
    PlanEntry("TC-UNI-FE-GRD-02", LEVEL_UNITARIA, SECTION_7_2_5_1,
              "Token caducado → canActivate=false, redirige /login",           TECH_CE_BC, TOOL_JEST),
    PlanEntry("TC-UNI-FE-GRD-03", LEVEL_UNITARIA, SECTION_7_2_5_1,
              "Token ausente → canActivate=false, redirige /login",            TECH_CE_BC, TOOL_JEST),
    PlanEntry("TC-UNI-FE-GRD-04", LEVEL_UNITARIA, SECTION_7_2_5_1,
              "U1/VIEWER en /releases/verify → canActivate=false, /forbidden", TECH_CE_BC, TOOL_JEST),

    # ── §7.2.5.2 Servicios HTTP Angular ───────────────────────────────────
    PlanEntry("TC-UNI-FE-SVC-01", LEVEL_UNITARIA, SECTION_7_2_5_2,
              "POST /releases 201 → Observable emite Release, Bearer presente",TECH_BASE_CHOICE, TOOL_JEST),
    PlanEntry("TC-UNI-FE-SVC-02", LEVEL_UNITARIA, SECTION_7_2_5_2,
              "POST /releases 401 → Observable emite AuthError",               TECH_BASE_CHOICE, TOOL_JEST),
    PlanEntry("TC-UNI-FE-SVC-03", LEVEL_UNITARIA, SECTION_7_2_5_2,
              "POST /releases 422 → Observable emite ValidationError",         TECH_BASE_CHOICE, TOOL_JEST),

    # ── §7.2.5.3 Efectos NgRx ─────────────────────────────────────────────
    PlanEntry("TC-UNI-FE-NGR-01", LEVEL_UNITARIA, SECTION_7_2_5_3,
              "API 202+taskId → verifyReleaseSuccess con taskId",              TECH_CE, TOOL_JEST),
    PlanEntry("TC-UNI-FE-NGR-02", LEVEL_UNITARIA, SECTION_7_2_5_3,
              "API 409 → verifyReleaseFailure con INVALID_STATE",              TECH_CE, TOOL_JEST),

    # ── §7.3.1 Ciclo de vida release ──────────────────────────────────────
    PlanEntry("TC-INT-EST-01", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T1 BORRADOR→EN_VERIFICACION → HTTP 202",         TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-02", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T2 EN_VERIFICACION→VÁLIDA",                      TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-03", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T3 EN_VERIFICACION→CON_ADVERTENCIAS",            TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-04", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T4 EN_VERIFICACION→NO_VÁLIDA",                   TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-05", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T5 VÁLIDA→ARCHIVADA (inmutable)",                TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-06", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T6 NO_VÁLIDA→EN_VERIFICACION (rework)",          TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-07", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T-NEG ARCHIVADA→EN_VERIFICACION → 409",          TECH_TE, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-EST-08", LEVEL_INTEGRACION, SECTION_7_3_1,
              "T-NEG BORRADOR→VÁLIDA (salto) → 422",            TECH_TE, TOOL_PYTEST_DOCKER),

    # ── §7.3.2 Flujo / rate limit / resiliencia ───────────────────────────
    PlanEntry("TC-INT-FLW-01", LEVEL_INTEGRACION, SECTION_7_3_2,
              "CU-01 todas RV-01..10 conectores activos → VALID",   TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-FLW-02", LEVEL_INTEGRACION, SECTION_7_3_2,
              "CU-01 conector GitLab INACTIVO → _WITH_INCIDENTS",   TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-FLW-03", LEVEL_INTEGRACION, SECTION_7_3_2,
              "Re-verificación tras NO_VÁLIDA → VÁLIDA",             TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-LIM-01", LEVEL_INTEGRACION, SECTION_7_3_2,
              "VL rate limit petición 100/60s → 200",               TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-LIM-02", LEVEL_INTEGRACION, SECTION_7_3_2,
              "VL rate limit petición 101/60s → 429+Retry-After",   TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-RES-01", LEVEL_INTEGRACION, SECTION_7_3_2,
              "docker kill worker durante verificación → sin corrupción",TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-RES-02", LEVEL_INTEGRACION, SECTION_7_3_2,
              "Redis caído al lanzar POST /verify → 503",            TECH_VL, TOOL_PYTEST_DOCKER),
    PlanEntry("TC-INT-MIG-01", LEVEL_INTEGRACION, SECTION_7_3_2,
              "alembic upgrade head sobre BD vacía → esquema OK",    TECH_VL, TOOL_PYTEST_DOCKER),

    # ── §7.4 Aceptación + Usabilidad ──────────────────────────────────────
    PlanEntry("TC-ACP-CU-00", LEVEL_ACEPTACION, SECTION_7_4,
              "CU-01 base → VÁLIDA en ≤5 acciones (RNF-19)",        "BC", TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-ACP-CU-01", LEVEL_ACEPTACION, SECTION_7_4,
              "CU-01 RV-04=WARNING → semáforo naranja",              "BC", TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-ACP-CU-02", LEVEL_ACEPTACION, SECTION_7_4,
              "CU-01 RV-05=ERROR → semáforo rojo, msg descriptivo",  "BC", TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-ACP-CU-03", LEVEL_ACEPTACION, SECTION_7_4,
              "Usuario nuevo completa flujo en ≤15 min (RNF-24)",    "BC", TOOL_MANUAL),
    PlanEntry("TC-ACP-UI-01", LEVEL_ACEPTACION, SECTION_7_4,
              "Snapshot inmutable tras archivar (RNF-36)",            "BC", TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-ACP-FRM-01",LEVEL_ACEPTACION, SECTION_7_4,
              "Campo obligatorio vacío → mensaje campo+acción",       TECH_VL, TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-ACP-FRM-02",LEVEL_ACEPTACION, SECTION_7_4,
              "Campo numérico con texto → error de tipo (RNF-20)",    TECH_VL, TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-USA-NAV-01",LEVEL_ACEPTACION, SECTION_7_4,
              "Each choice Chrome/Firefox/Edge/Safari (RNF-29)",      "EC", TOOL_CYPRESS),
    PlanEntry("TC-USA-RES-01",LEVEL_ACEPTACION, SECTION_7_4,
              "VL resolución 1920/768/375 → sin desbordamiento (RNF-30)",TECH_VL,TOOL_MANUAL_CYPRESS),
    PlanEntry("TC-USA-SEM-01",LEVEL_ACEPTACION, SECTION_7_4,
              "Semáforo coherente en dashboard/historial/detalle (RNF-21)","EC",TOOL_MANUAL_CYPRESS),

    # ── §7.5 Rendimiento ──────────────────────────────────────────────────
    PlanEntry("TC-PER-VL-01", LEVEL_RENDIMIENTO, SECTION_7_5,
              "Verificación 10 reglas → tiempo e2e ≤5s p95 (RNF-06)", TECH_VL, TOOL_LOCUST),
    PlanEntry("TC-PER-VL-02", LEVEL_RENDIMIENTO, SECTION_7_5,
              "Motor Rust bucle → p95 <500ms (RNF-07)",               TECH_VL, TOOL_LOCUST),
    PlanEntry("TC-PER-VL-03", LEVEL_RENDIMIENTO, SECTION_7_5,
              "50 POST /verify simultáneos → todas 202 (RNF-06)",     TECH_VL, TOOL_LOCUST),
    PlanEntry("TC-PER-CE-04", LEVEL_RENDIMIENTO, SECTION_7_5,
              "Suite completa → SonarCloud cobertura ≥70% (RNF-27)",  TECH_CE, TOOL_SONARCLOUD),

    # ── §7.6 Seguridad ────────────────────────────────────────────────────
    PlanEntry("TC-SEC-AUT-01",LEVEL_SEGURIDAD, SECTION_7_6,
              "VL fuerza bruta: 5 intentos → 403 + bloqueo 15min (RNF-14)",TECH_CE,TOOL_PYTEST),
    PlanEntry("TC-SEC-AUT-02",LEVEL_SEGURIDAD, SECTION_7_6,
              "JWT manipulado → 401 (OWASP A2)",                      TECH_CE, TOOL_PYTEST),
    PlanEntry("TC-SEC-INY-01",LEVEL_SEGURIDAD, SECTION_7_6,
              "SQLi en nombre release → neutralizado (OWASP A3)",     TECH_CE, TOOL_PYTEST),
    PlanEntry("TC-SEC-INY-02",LEVEL_SEGURIDAD, SECTION_7_6,
              "XSS en release → escapado al frontend (OWASP A3)",     TECH_CE, TOOL_PYTEST),
    PlanEntry("TC-SEC-CIF-01",LEVEL_SEGURIDAD, SECTION_7_6,
              "Credenciales cifradas AES-256-GCM en BD (RNF-13)",     TECH_CE, TOOL_PYTEST),
]

# Índice rápido TC-ID → PlanEntry
PLAN_INDEX: dict[str, PlanEntry] = {e.tc_id: e for e in PLAN}

assert len(PLAN) == 77, f"El plan debe tener 77 casos, tiene {len(PLAN)}"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE COLOR ANSI
# ─────────────────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
GREY   = "\033[90m"
WHITE  = "\033[97m"

def no_color(text: str) -> str:
    """Strip ANSI codes (for file output)."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE TC-IDs DESDE TEXTO
# ─────────────────────────────────────────────────────────────────────────────

# Patrón que captura TC-IDs con guiones o guiones bajos:
#   TC-UNI-AGG-01  TC_UNI_AGG_01  tc-uni-agg-01
#   test_TC_UNI_AGG_01_desc  (nombre de función pytest/cargo/jest)
#   TC-UNI-FE-GRD-01  TC_UNI_FE_GRD_01
# Se usa lookaround porque _ es carácter de palabra y bloquearía \b
# en nombres como test_TC_UNI_AGG_01.
_TC_RAW = re.compile(
    r"(?<![A-Za-z])"                           # no precedido por letra
    r"(TC[-_]"                                 # prefijo TC- o TC_
    r"(?:UNI|INT|ACP|USA|PER|SEC)[-_]"        # nivel
    r"(?:FE[-_])?"                             # opcional subgrupo FE-
    r"[A-Z]+[-_]"                              # grupo
    r"\d+)"                                    # número
    r"(?![A-Za-z])",                           # no seguido de letra
    re.IGNORECASE,
)

# Detecta si una línea indica FALLO en el test que contiene el TC-ID
_FAIL_MARKERS = re.compile(
    r"\bFAILED|✗|✕|●|\bERROR\b|\bFAIL\b|PANICKED",
    re.IGNORECASE,
)

_PASS_MARKERS = re.compile(
    r"\bPASSED\b|\bPASS\b|✓|✔|\bok\b|\bOK\b",
    re.IGNORECASE,
)


def _normalise(raw: str) -> str:
    """TC_UNI_AGG_01 → TC-UNI-AGG-01  (mayúsculas, guiones)."""
    return raw.upper().replace("_", "-")


def parse_text(content: str) -> dict[str, str]:
    """
    Extrae TC-IDs de salida de texto libre (pytest -v, cargo test, jest --verbose).
    Devuelve {tc_id: "PASS" | "FAIL"}.
    """
    results: dict[str, str] = {}
    for line in content.splitlines():
        found = _TC_RAW.findall(line)
        if not found:
            continue
        status = "FAIL" if _FAIL_MARKERS.search(line) else "PASS"
        for raw in found:
            tc_id = _normalise(raw)
            # Si ya vimos este ID como FAIL, no lo sobreescribimos con PASS
            if results.get(tc_id) != "FAIL":
                results[tc_id] = status
    return results


def parse_junit_xml(content: str) -> dict[str, str]:
    """
    Extrae TC-IDs de informes JUnit XML (pytest --junit-xml / jest-junit).
    Busca en classname, name y message.
    """
    results: dict[str, str] = {}
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return results

    for tc in root.iter("testcase"):
        text = " ".join(filter(None, [
            tc.get("name", ""),
            tc.get("classname", ""),
            tc.findtext("failure") or "",
            tc.findtext("error") or "",
        ]))
        found = _TC_RAW.findall(text)
        if not found:
            continue
        has_failure = tc.find("failure") is not None or tc.find("error") is not None
        status = "FAIL" if has_failure else "PASS"
        for raw in found:
            tc_id = _normalise(raw)
            if results.get(tc_id) != "FAIL":
                results[tc_id] = status
    return results


def parse_file(path: Path) -> dict[str, str]:
    """Detecta formato y delega al parser adecuado."""
    content = path.read_text(encoding="utf-8", errors="replace")
    stripped = content.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<testsuites") or stripped.startswith("<testsuite"):
        return parse_junit_xml(content)
    return parse_text(content)


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS Y REPORTE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TraceReport:
    passed:  list[PlanEntry] = field(default_factory=list)   # implementado y pasa
    failed:  list[PlanEntry] = field(default_factory=list)   # implementado pero falla
    missing: list[PlanEntry] = field(default_factory=list)   # no encontrado en ningún output
    unknown: list[str]       = field(default_factory=list)   # TC-IDs en los tests no en el plan


def analyse(results: dict[str, str]) -> TraceReport:
    report = TraceReport()
    seen = set(results.keys())

    for entry in PLAN:
        if entry.tc_id not in seen:
            report.missing.append(entry)
        elif results[entry.tc_id] == "FAIL":
            report.failed.append(entry)
        else:
            report.passed.append(entry)

    for tc_id in sorted(seen):
        if tc_id not in PLAN_INDEX:
            report.unknown.append(tc_id)

    return report


def _status_icon(lmiss: int, lfail: int) -> str:
    if lmiss == 0 and lfail == 0:
        return GREEN + "✓" + RESET
    if lfail > 0:
        return RED + "✗" + RESET
    return YELLOW + "?" + RESET


def _print_level_details(report: TraceReport) -> None:
    levels = [LEVEL_UNITARIA, LEVEL_INTEGRACION, LEVEL_ACEPTACION, LEVEL_RENDIMIENTO, LEVEL_SEGURIDAD]
    for level in levels:
        level_entries = [e for e in PLAN if e.level == level]
        lpass = sum(1 for e in level_entries if e in report.passed)
        lfail = sum(1 for e in level_entries if e in report.failed)
        lmiss = sum(1 for e in level_entries if e in report.missing)
        print(f"  {_status_icon(lmiss, lfail)} {BOLD}{level:<14}{RESET}  "
              f"{GREEN}pass={lpass:<3}{RESET} {RED}fail={lfail:<3}{RESET} "
              f"{YELLOW}miss={lmiss:<3}{RESET}  ({len(level_entries)} en plan)")


def _print_failed_tests(report: TraceReport) -> None:
    if report.failed:
        print(f"\n{BOLD}{RED}  ✗ CASOS QUE FALLAN ({len(report.failed)}){RESET}")
        for e in report.failed:
            print(f"    {RED}{e.tc_id:<22}{RESET}  {e.section:<8}  {e.description[:55]}")


def _print_missing_tests(report: TraceReport) -> None:
    if report.missing:
        print(f"\n{BOLD}{YELLOW}  ? CASOS SIN IMPLEMENTAR ({len(report.missing)}){RESET}")
        by_section: dict[str, list[PlanEntry]] = defaultdict(list)
        for e in report.missing:
            by_section[e.section].append(e)
        for section in sorted(by_section):
            print(f"    {GREY}{section}{RESET}")
            for e in by_section[section]:
                print(f"      {YELLOW}{e.tc_id:<22}{RESET}  {e.tool:<18}  "
                      f"{e.description[:45]}")


def _print_unknown_tests(report: TraceReport) -> None:
    if report.unknown:
        print(f"\n{BOLD}{GREY}  ⚠ TC-IDs EN TESTS NO PRESENTES EN EL PLAN ({len(report.unknown)}){RESET}")
        print(f"    {GREY}(puede ser un ID mal escrito o un test fuera del plan){RESET}")
        for tc_id in report.unknown:
            print(f"    {GREY}{tc_id}{RESET}")


def print_report(report: TraceReport) -> None:
    total = len(PLAN)
    n_pass = len(report.passed)
    n_fail = len(report.failed)
    n_miss = len(report.missing)
    coverage_pct = n_pass / total * 100

    print()
    print(f"{BOLD}{WHITE}{'─'*70}{RESET}")
    print(f"{BOLD}{WHITE}  SVAES — Informe de Trazabilidad Plan de Pruebas{RESET}")
    print(f"{BOLD}{WHITE}{'─'*70}{RESET}")
    print(f"  Plan total : {total} casos")
    print(f"  {GREEN}✓ Cubiertas y pasan : {n_pass:>3}  ({n_pass/total*100:.1f}%){RESET}")
    print(f"  {RED}✗ Fallan             : {n_fail:>3}{RESET}")
    print(f"  {YELLOW}? Sin implementar    : {n_miss:>3}{RESET}")
    if report.unknown:
        print(f"  {GREY}⚠ TC-IDs no en plan  : {len(report.unknown):>3}{RESET}")

    bar_len = 50
    filled = int(bar_len * n_pass / total)
    fail_f = int(bar_len * n_fail / total)
    miss_f = bar_len - filled - fail_f
    bar = (f"{GREEN}{'█'*filled}{RESET}"
           f"{RED}{'█'*fail_f}{RESET}"
           f"{YELLOW}{'░'*miss_f}{RESET}")
    print(f"\n  [{bar}] {coverage_pct:.1f}% cubiertas y OK\n")

    _print_level_details(report)
    _print_failed_tests(report)
    _print_missing_tests(report)
    _print_unknown_tests(report)

    print(f"\n{BOLD}{WHITE}{'─'*70}{RESET}\n")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTACIÓN A MARKDOWN Y CSV
# ─────────────────────────────────────────────────────────────────────────────

def export_markdown(report: TraceReport, path: Path) -> None:
    STATUS_ICON = {"PASS": "✅", "FAIL": "❌", "MISSING": "⬜"}
    lines = [
        "# Informe de trazabilidad — SVAES Plan de Pruebas\n",
        f"**Total en plan:** {len(PLAN)}  |  "
        f"**Cubiertas OK:** {len(report.passed)}  |  "
        f"**Fallan:** {len(report.failed)}  |  "
        f"**Sin implementar:** {len(report.missing)}\n",
        "| TC-ID | Nivel | Sección | Estado | Herramienta | Descripción |",
        "|---|---|---|---|---|---|",
    ]
    result_map = (
        {e.tc_id: "PASS"    for e in report.passed}
        | {e.tc_id: "FAIL"   for e in report.failed}
        | {e.tc_id: "MISSING" for e in report.missing}
    )
    for entry in PLAN:
        st = result_map[entry.tc_id]
        icon = STATUS_ICON[st]
        lines.append(
            f"| `{entry.tc_id}` | {entry.level} | {entry.section} "
            f"| {icon} {st} | {entry.tool} | {entry.description} |"
        )
    if report.unknown:
        lines += [
            "\n## TC-IDs en tests no reconocidos en el plan\n",
            *[f"- `{tc_id}`" for tc_id in report.unknown],
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → Markdown exportado: {path}")


def export_csv(report: TraceReport, path: Path) -> None:
    result_map = (
        {e.tc_id: "PASS"    for e in report.passed}
        | {e.tc_id: "FAIL"   for e in report.failed}
        | {e.tc_id: "MISSING" for e in report.missing}
    )
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["TC-ID", "Nivel", "Sección", "Estado",
                    "Técnica", "Herramienta", "Descripción"])
        for entry in PLAN:
            w.writerow([
                entry.tc_id, entry.level, entry.section,
                result_map[entry.tc_id],
                entry.technique, entry.tool, entry.description,
            ])
    print(f"  → CSV exportado: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def _read_from_stdin() -> dict[str, str]:
    print(f"{CYAN}Leyendo de stdin (pega la salida de los tests y pulsa Ctrl+D)...{RESET}")
    content = sys.stdin.read()
    return parse_text(content)


def _process_file_args(args: list[str]) -> dict[str, str]:
    results: dict[str, str] = {}
    for arg in args:
        p = Path(arg)
        if not p.exists():
            print(f"{RED}⚠ Archivo no encontrado: {arg}{RESET}", file=sys.stderr)
            continue
        partial = parse_file(p)
        print(f"{GREY}  Leído {p.name}: {len(partial)} TC-IDs encontrados{RESET}")
        for tc_id, status in partial.items():
            if results.get(tc_id) != "FAIL":
                results[tc_id] = status
    return results


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    all_results = _read_from_stdin() if not args else _process_file_args(args)

    report = analyse(all_results)
    print_report(report)

    out_dir = Path("tests/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    export_markdown(report, out_dir / "traceability_report.md")
    export_csv(report, out_dir / "traceability_report.csv")
    print()

    return 0 if (not report.missing and not report.failed) else 1


if __name__ == "__main__":
    sys.exit(main())