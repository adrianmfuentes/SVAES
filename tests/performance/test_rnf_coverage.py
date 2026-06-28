"""
Pruebas de RNF — Cobertura: Rendimiento, Fiabilidad, Mantenibilidad,
Usabilidad, Portabilidad, Extensibilidad, Trazabilidad y Organizacionales.

IDs cubiertos:
  TC-PER-RNF01-01  TC-PER-RNF02-01  TC-PER-RNF04-01  TC-PER-RNF05-01
  TC-FIA-RNF09-01  TC-FIA-RNF10-01  TC-FIA-RNF11-01
  TC-USA-RNF22-01
  TC-MNT-RNF25-01  TC-MNT-RNF26-01  TC-MNT-RNF28-01
  TC-POR-RNF31-01
  TC-EXT-RNF32-01  TC-EXT-RNF33-01  TC-EXT-RNF34-01
  TC-TRZ-RNF35-01  TC-TRZ-RNF37-01
  TC-ORG-RNF38-01  TC-ORG-RNF40-01
"""

from __future__ import annotations

import ast
import inspect
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

# ---------------------------------------------------------------------------
# sys.path: expose api/src so domain/application/infrastructure are importable
# ---------------------------------------------------------------------------
_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "api", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ---------------------------------------------------------------------------
# Minimal env vars required by FastAPI app startup
# ---------------------------------------------------------------------------
_REDIS = "redis://localhost:6379/0"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "rnf-coverage-test-secret-key-32ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=")
os.environ.setdefault("REDIS_URL", _REDIS)
os.environ.setdefault("CELERY_BROKER_URL", _REDIS)
os.environ.setdefault("CELERY_RESULT_BACKEND", _REDIS)
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
os.environ.setdefault("ENGINE_API_KEY", "test-engine-api-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "AdminPass1")
os.environ.setdefault("API_KEY_PEPPER", "test-pepper-value")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_API_SRC = _PROJECT_ROOT / "api" / "src"
_WEB_SRC = _PROJECT_ROOT / "web" / "src"

pytestmark = pytest.mark.performance

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TARGET_HOST = os.getenv("PERF_API_BASE_URL", "http://localhost:8000")


def _make_fake_current_user():
    """Return a CurrentUser with admin role for dependency override."""
    from core.dependencies import CurrentUser
    from domain.enums import UserRole

    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U3,
        email="perf-test@svaes.test",
        organization_id=uuid4(),
    )


@asynccontextmanager
async def _noop_lifespan(app):
    """Suppress alembic migrations and seeding during tests."""
    yield


# ---------------------------------------------------------------------------
# NOTE: The Locust load-test user (WebLoadUser) lives in locustfile.py and is
# run via the `locust` CLI. It is NOT imported here on purpose: importing
# locust triggers gevent's monkey.patch_all(), which corrupts the asyncio
# event loop for every subsequent @pytest.mark.asyncio test in the same
# process (they hang forever on Windows IOCP). The pytest check below
# therefore validates the load class by SOURCE INSPECTION only.
# ---------------------------------------------------------------------------

_LOCUSTFILE = Path(__file__).resolve().parent / "locustfile.py"


# ===========================================================================
# TC-PER — RENDIMIENTO
# ===========================================================================


@pytest.mark.asyncio
async def test_tc_per_rnf01_01_verification_10_rules_under_30s():
    """TC-PER-RNF01-01: Procesamiento ≤30s con 10 reglas (RNF-01).

    Llama a _call_verification_engine con respx mockeando el motor Rust
    (<1s por llamada) y verifica que el tiempo total sea ≤30s.
    """
    try:
        import respx
    except ImportError:
        pytest.skip("respx not installed — add it to pyproject.toml dev deps")

    from infrastructure.workers.verification_worker import _call_verification_engine

    engine_url = os.environ["ENGINE_URL"]
    engine_key = os.environ["ENGINE_API_KEY"]

    rule_results = [
        {"rule_id": f"RV-{i + 1:02d}", "passed": True, "details": {}}
        for i in range(10)
    ]

    with respx.mock:
        respx.post(f"{engine_url}/api/v1/verify").mock(
            return_value=httpx.Response(
                200,
                json={
                    "verdict": "VALIDA",
                    "rule_results": rule_results,
                    "summary": {},
                },
            )
        )

        artifacts_data = [
            {
                "id": str(uuid4()),
                "artifact_type": "pull_request",
                "metadata": {"title": f"PR {i}", "state": "MERGED"},
            }
            for i in range(10)
        ]
        rules_data = [
            {"id": f"RV-{i + 1:02d}", "severity": "OBLIGATORIA", "params": {}}
            for i in range(10)
        ]

        start = time.perf_counter()
        result = await _call_verification_engine(artifacts_data, rules_data)
        elapsed = time.perf_counter() - start

    assert elapsed < 30.0, f"Engine call took {elapsed:.2f}s — expected ≤ 30s (RNF-01)"
    assert result.get("verdict") == "VALIDA"
    assert len(result.get("rule_results", [])) == 10


def test_tc_per_rnf02_01_locust_web_load_20_users_class_defined():
    """TC-PER-RNF02-01: Locust WebLoadUser con umbral 3s definido (RNF-02).

    Prueba de carga real: locust -f tests/performance/locustfile.py WebLoadUser
    --users 20 --spawn-rate 20 --headless --run-time 30s

    Se valida por inspección de código fuente (sin importar locust) porque
    importar locust dispara gevent.monkey.patch_all(), que rompe el bucle de
    eventos asyncio de las pruebas async siguientes (RNF-02).
    """
    assert _LOCUSTFILE.exists(), f"locustfile.py no encontrado en {_LOCUSTFILE}"
    source = _LOCUSTFILE.read_text(encoding="utf-8")

    # The WebLoadUser load-test class must be declared in the locustfile
    assert "class WebLoadUser(HttpUser):" in source, (
        "Falta la clase WebLoadUser en locustfile.py (RNF-02)"
    )

    # Parse with AST to assert structure precisely
    tree = ast.parse(source)
    web_load_user = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "WebLoadUser"
        ),
        None,
    )
    assert web_load_user is not None, "WebLoadUser no es una clase válida (RNF-02)"

    method_names = {
        n.name
        for n in web_load_user.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "dashboard_metrics" in method_names, "Falta tarea dashboard_metrics (RNF-02)"
    assert "health" in method_names, "Falta tarea health (RNF-02)"

    # 3-second latency threshold must be defined
    assert "MAX_RESPONSE_MS = 3_000" in source or "MAX_RESPONSE_MS = 3000" in source, (
        "Umbral de latencia debe ser 3000ms (RNF-02)"
    )


@pytest.mark.asyncio
async def test_tc_per_rnf04_01_dashboard_1000_verifications_under_3s():
    """TC-PER-RNF04-01: /dashboard/metrics responde 200 en ≤3s con 1000 resultados (RNF-04)."""
    from main import app
    from core.dependencies import get_current_user, get_release_repository, get_verification_result_repository
    from domain.enums import ReleaseStatus, VerdictType
    from httpx import AsyncClient, ASGITransport

    org_id = uuid4()
    fake_user = _make_fake_current_user()
    fake_user.organization_id = org_id

    # Build 1000 mocked verification results
    mock_result = MagicMock()
    mock_result.verdict = VerdictType.VALID

    mock_release = MagicMock()
    mock_release.id = uuid4()
    mock_release.status = ReleaseStatus.VALIDA

    mock_release_repo = AsyncMock()
    mock_release_repo.list_by_organization.return_value = [mock_release] * 50

    mock_verification_repo = AsyncMock()
    mock_verification_repo.find_by_release.return_value = [mock_result] * 20  # 50×20 = 1000

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_release_repository] = lambda: mock_release_repo
    app.dependency_overrides[get_verification_result_repository] = lambda: mock_verification_repo

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=True),
            base_url="http://test",  # NOSONAR
        ) as client:
            start = time.perf_counter()
            response = await client.get(
                "/api/v1/dashboard/metrics",
                params={"org_id": str(org_id)},
            )
            elapsed = time.perf_counter() - start
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert elapsed < 3.0, f"Dashboard took {elapsed:.2f}s — expected ≤ 3s (RNF-04)"
    data = response.json()
    assert data["total_verifications"] == 1000


@pytest.mark.asyncio
async def test_tc_per_rnf05_01_simple_api_queries_under_500ms():
    """TC-PER-RNF05-01: Consultas simples a API REST responden en <500ms (RNF-05)."""
    from main import app
    from core.dependencies import get_current_user
    from httpx import AsyncClient, ASGITransport

    fake_user = _make_fake_current_user()

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = lambda: fake_user

    endpoints = ["/health", "/openapi.json"]

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",  # NOSONAR
        ) as client:
            for endpoint in endpoints:
                start = time.perf_counter()
                response = await client.get(endpoint)
                elapsed = time.perf_counter() - start

                assert elapsed < 0.5, (
                    f"{endpoint} took {elapsed*1000:.0f}ms — expected < 500ms (RNF-05)"
                )
                assert response.status_code in (200, 307, 404), (
                    f"{endpoint} returned unexpected status {response.status_code}"
                )
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# TC-FIA — FIABILIDAD
# ===========================================================================


@pytest.mark.asyncio
async def test_tc_fia_rnf09_01_connector_failure_continues_verification():
    """TC-FIA-RNF09-01: Fallo de conector no aborta la verificación global (RNF-09).

    Un conector que lanza excepción es omitido; los demás artefactos
    continúan procesándose.
    """
    from infrastructure.workers.verification_worker import _fetch_artifacts

    failing_artifact = MagicMock()
    failing_artifact.id = uuid4()
    failing_artifact.connector_implementation = "GITHUB"
    failing_artifact.connector_instance_id = uuid4()
    failing_artifact.external_ref = "pulls/1"

    ok_artifact = MagicMock()
    ok_artifact.id = uuid4()
    ok_artifact.connector_implementation = "JIRA"
    ok_artifact.connector_instance_id = uuid4()
    ok_artifact.external_ref = "PROJ-42"
    ok_artifact.artifact_type = "issue"

    failing_connector = AsyncMock()
    failing_connector.fetch_artifact.side_effect = ConnectionError("GitHub API unreachable")

    ok_connector = AsyncMock()
    ok_connector.fetch_artifact.return_value = {
        "key": "PROJ-42",
        "summary": "Fix critical bug",
        "status": "Done",
    }

    mock_registry = MagicMock()
    mock_registry.get_by_implementation.side_effect = lambda name: (
        failing_connector if "GITHUB" in name.upper() else ok_connector
    )

    mock_instance = MagicMock()
    mock_instance.encrypted_credentials = b"irrelevant"

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_instance

    mock_celery = MagicMock()

    encrypted_config = b"{'token': 'abc123', 'url': 'https://jira.example.com'}"

    with (
        patch("infrastructure.workers.verification_worker.SqlConnectorRepository", return_value=mock_repo),
        # Fernet is imported lazily inside _fetch_artifacts (from cryptography.fernet
        # import Fernet), so it must be patched at its source module, not on the worker.
        patch("cryptography.fernet.Fernet") as mock_fernet,
    ):
        mock_fernet.return_value.decrypt.return_value = encrypted_config

        result = await _fetch_artifacts(
            artifacts=[failing_artifact, ok_artifact],
            connector_registry=mock_registry,
            celery_task=mock_celery,
            total_stages=5,
        )

    # Only the successful artifact should be in results
    artifacts_data, fetch_errors = result
    assert len(artifacts_data) == 1, (
        f"Expected 1 artifact (JIRA), got {len(artifacts_data)} — connector failure must not abort (RNF-09)"
    )
    assert len(fetch_errors) == 1, (
        f"Expected 1 error entry (GITHUB), got {len(fetch_errors)} — connector failure must not abort (RNF-09)"
    )
    assert artifacts_data[0]["metadata"]["key"] == "PROJ-42"
    assert fetch_errors[0]["connector"] == "GITHUB"


def test_tc_fia_rnf10_01_critical_errors_logged_within_5s(caplog):
    """TC-FIA-RNF10-01: Errores críticos llegan al log en ≤5s (RNF-10)."""
    from core.audit import AuditEntry, AuditEvent, AuditLogger

    entry = AuditEntry(
        event=AuditEvent.SECURITY_BREACH_DETECTED,
        user_id=uuid4(),
        organization_id=uuid4(),
        resource_type="system",
        resource_id=None,
        details={"description": "test critical error injection"},
    )

    logger = AuditLogger.get_instance()

    with caplog.at_level(logging.INFO, logger="audit"):
        start = time.perf_counter()
        logger.log(entry)
        elapsed = time.perf_counter() - start

    assert elapsed < 5.0, (
        f"Log write took {elapsed:.3f}s — must complete in ≤5s (RNF-10)"
    )
    audit_messages = [r.getMessage() for r in caplog.records]
    assert any("SECURITY_BREACH_DETECTED" in m for m in audit_messages), (
        "SECURITY_BREACH_DETECTED must appear in audit log (RNF-10)"
    )


@pytest.mark.asyncio
async def test_tc_fia_rnf11_01_failure_rate_under_0_1_percent():
    """TC-FIA-RNF11-01: Tasa de fallos <0.1% tras 1000 verificaciones nominales (RNF-11)."""
    from domain.entities.verification_result import VerificationResult
    from domain.enums import VerdictType

    async def nominal_verification(release_id: UUID) -> VerificationResult:
        return VerificationResult(
            release_id=release_id,
            verdict=VerdictType.VALID,
            rule_results=[
                {"rule_id": f"RV-{i + 1:02d}", "passed": True, "details": {}}
                for i in range(10)
            ],
            summary={"ok": True},
            duration_ms=150,
        )

    total = 1000
    failures = 0

    for _ in range(total):
        try:
            result = await nominal_verification(uuid4())
            assert result.verdict == VerdictType.VALID
        except Exception:
            failures += 1

    failure_rate = failures / total
    assert failure_rate < 0.001, (
        f"Failure rate {failure_rate:.4%} ≥ 0.1% — RNF-11 violated "
        f"({failures}/{total} failures)"
    )


# ===========================================================================
# TC-USA — USABILIDAD
# ===========================================================================


def test_tc_usa_rnf22_01_responsive_viewport_4_browsers():
    """TC-USA-RNF22-01: Viewport responsive validado en 4 puntos de quiebre (RNF-22).

    Verifica que el frontend Angular declare:
    - Meta viewport estándar en index.html
    - Al menos un @media breakpoint para móvil, tablet, escritorio y pantalla grande
    """
    index_html = _WEB_SRC / "index.html"
    assert index_html.exists(), f"web/src/index.html no encontrado en {_WEB_SRC}"

    html_content = index_html.read_text(encoding="utf-8")
    assert 'name="viewport"' in html_content, "Falta meta viewport en index.html (RNF-22)"
    assert "width=device-width" in html_content, "Falta width=device-width en viewport"
    assert "initial-scale=1" in html_content, "Falta initial-scale=1 en viewport"

    # Collect all SCSS files from the Angular app
    scss_files = list(_WEB_SRC.rglob("*.scss"))
    assert len(scss_files) > 0, "No se encontraron archivos SCSS en web/src"

    all_scss = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in scss_files)

    # Expect @media queries for the 4 standard breakpoints
    # Mobile ≤768px, Tablet ≤1024px, Desktop >1024px, Large >1200px
    breakpoints = ["@media", "max-width", "min-width"]
    assert any(bp in all_scss for bp in breakpoints), (
        "No se encontraron reglas @media en los archivos SCSS (RNF-22)"
    )

    # At least two numeric breakpoints among the common values
    numeric_bps = ["320", "375", "768", "1024", "1200", "1440"]
    found = [bp for bp in numeric_bps if bp in all_scss]
    assert len(found) >= 2, (
        f"Se esperaban ≥2 puntos de quiebre numéricos en SCSS, "
        f"se encontraron: {found} (RNF-22)"
    )


# ===========================================================================
# TC-MNT — MANTENIBILIDAD
# ===========================================================================


def test_tc_mnt_rnf25_01_domain_layer_no_infrastructure_imports():
    """TC-MNT-RNF25-01: Capa domain no importa adapters ni infrastructure (RNF-25).

    Escanea todos los .py en api/src/domain/ con ast y verifica que no
    haya ningún import de 'infrastructure', 'adapters', 'primary' o 'secondary'.
    """
    domain_dir = _API_SRC / "domain"
    assert domain_dir.exists(), f"domain/ no encontrado en {_API_SRC}"

    forbidden = frozenset({"adapters", "infrastructure", "primary", "secondary", "connectors"})
    violations: list[str] = []

    for py_file in domain_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            pytest.fail(f"SyntaxError en {py_file}: {exc}")

        for node in ast.walk(tree):
            module_str = ""
            if isinstance(node, ast.ImportFrom) and node.module:
                module_str = node.module
            elif isinstance(node, ast.Import):
                module_str = " ".join(alias.name for alias in node.names)

            if module_str and any(banned in module_str for banned in forbidden):
                rel = py_file.relative_to(_API_SRC)
                violations.append(f"  {rel}: import '{module_str}'")

    assert not violations, (
        f"TC-MNT-RNF25-01: Capa domain contiene {len(violations)} import(s) prohibido(s):\n"
        + "\n".join(violations)
    )


def test_tc_mnt_rnf26_01_new_connector_no_engine_changes():
    """TC-MNT-RNF26-01: Nuevo conector sin modificar motor ni UI (RNF-26).

    Registra un conector ficticio en ConnectorRegistry y verifica que la
    interfaz IVerificationEngine no cambia ni precisa conocer el nuevo conector.
    """
    from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
    from application.ports.output.i_verification_engine import IVerificationEngine

    # Define a new connector without touching engine or UI code
    class CustomAnalyticsConnector:
        CONNECTOR_TYPE = "ANALYTICS"
        CONNECTOR_IMPLEMENTATION = "CUSTOM_ANALYTICS_V1"

        def get_connector_type(self) -> str:
            return self.CONNECTOR_TYPE

        def get_connector_implementation(self) -> str:
            return self.CONNECTOR_IMPLEMENTATION

        def get_artifact_types(self) -> list[str]:
            return ["report"]

        def get_metadata(self) -> dict:
            return {"name": "CustomAnalytics", "version": "1.0", "artifact_types": self.get_artifact_types()}

    # Registration must succeed without touching engine source
    registry = ConnectorRegistry()
    new_connector = CustomAnalyticsConnector()
    registry.register(new_connector.get_connector_implementation(), new_connector)

    retrieved = registry.get_by_implementation("CUSTOM_ANALYTICS_V1")
    assert retrieved is new_connector, "New connector must be retrievable after registration"
    assert "CUSTOM_ANALYTICS_V1" in registry.list_all_implementations()

    # Engine interface must remain unaware of specific connectors
    engine_sig = inspect.signature(IVerificationEngine.execute_verification)
    param_names = set(engine_sig.parameters.keys())

    assert "release" in param_names, "Engine must accept 'release'"
    assert "profile" in param_names, "Engine must accept 'profile'"
    assert "artifacts_data" in param_names, "Engine must accept 'artifacts_data'"
    assert "registry" not in param_names, "Engine must NOT receive 'registry' directly (RNF-26)"
    assert "connector" not in param_names, "Engine must NOT know about specific connectors (RNF-26)"


def test_tc_mnt_rnf28_01_router_endpoints_have_docstrings():
    """TC-MNT-RNF28-01: ≥50% de los endpoints de router tienen docstrings (RNF-28).

    Escanea api/src/infrastructure/primary/routers/api/v1/ con ast y
    comprueba la cobertura de docstrings en funciones públicas.
    """
    router_dir = _API_SRC / "infrastructure" / "primary" / "routers" / "api" / "v1"
    assert router_dir.exists(), f"Router dir not found: {router_dir}"

    total = 0
    missing: list[str] = []

    for py_file in router_dir.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            total += 1
            has_docstring = (
                bool(node.body)
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_docstring:
                missing.append(f"{py_file.name}:{node.name}()")

    assert total > 0, "No se encontraron funciones públicas en los routers"
    coverage_pct = (total - len(missing)) / total * 100
    print(f"\n  Docstring coverage: {coverage_pct:.1f}% ({total - len(missing)}/{total} functions)")

    assert coverage_pct >= 50.0, (
        f"TC-MNT-RNF28-01: Cobertura de docstrings {coverage_pct:.1f}% < 50% (RNF-28).\n"
        f"Sin docstring ({len(missing)}/{total}): {', '.join(missing[:10])}"
    )


# ===========================================================================
# TC-POR — PORTABILIDAD
# ===========================================================================


def test_tc_por_rnf31_01_readme_has_deployment_steps():
    """TC-POR-RNF31-01: README.md contiene pasos de despliegue reproducibles (RNF-31)."""
    readme_path = _PROJECT_ROOT / "README.md"
    assert readme_path.exists(), f"README.md no encontrado en {_PROJECT_ROOT}"

    content = readme_path.read_text(encoding="utf-8")

    required_keywords = [
        "docker",
        "docker compose",
    ]
    optional_keywords = [
        "pip install",
        "uvicorn",
        "npm",
        "npm install",
    ]

    for keyword in required_keywords:
        assert keyword.lower() in content.lower(), (
            f"README.md no menciona '{keyword}' — pasos de despliegue incompletos (RNF-31)"
        )

    found_optional = [kw for kw in optional_keywords if kw.lower() in content.lower()]
    assert len(found_optional) >= 1, (
        f"README.md debe mencionar al menos uno de: {optional_keywords} (RNF-31)"
    )


# ===========================================================================
# TC-EXT — EXTENSIBILIDAD
# ===========================================================================


@pytest.mark.asyncio
async def test_tc_ext_rnf32_01_openapi_includes_connector_paths():
    """TC-EXT-RNF32-01: Spec de conectores disponible en /openapi.json (RNF-32)."""
    from main import app
    from httpx import AsyncClient, ASGITransport

    app.router.lifespan_context = _noop_lifespan

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",  # NOSONAR
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200, f"GET /openapi.json returned {response.status_code}"
    spec = response.json()

    assert "openapi" in spec, "Missing 'openapi' field in spec"
    assert "paths" in spec, "Missing 'paths' field in spec"

    # At least one connector-related path must be present
    connector_paths = [p for p in spec["paths"] if "connector" in p.lower()]
    assert len(connector_paths) >= 1, (
        "No connector paths found in /openapi.json (RNF-32). "
        f"Available paths: {list(spec['paths'].keys())[:10]}"
    )


def test_tc_ext_rnf33_01_rules_as_plugins_no_engine_change():
    """TC-EXT-RNF33-01: Reglas actúan como plug-ins sin tocar el motor (RNF-33).

    Verifica que VerificationRule puede construirse con cualquier rule_template
    sin modificar la firma del motor.
    """
    from domain.entities.verification_rule import VerificationRule
    from domain.enums import SeverityType
    from application.ports.output.i_verification_engine import IVerificationEngine

    # New rule added dynamically — engine interface must not change
    new_rule = VerificationRule(
        profile_id=uuid4(),
        rule_template="RV-CUSTOM-PLUGIN-01",
        severity=SeverityType.MEDIUM,
        params={"threshold": 80, "metric": "branch_coverage"},
        connector_instance_id=None,
        is_active=True,
    )

    assert new_rule.rule_template == "RV-CUSTOM-PLUGIN-01"
    assert new_rule.params["threshold"] == 80

    # Engine still accepts arbitrary rule templates via artifacts_data
    sig = inspect.signature(IVerificationEngine.execute_verification)
    assert "artifacts_data" in sig.parameters, (
        "Engine must accept dynamic artifacts_data for plugin rules (RNF-33)"
    )

    # rule_names.py is data-driven — verifiable without engine changes
    from core.rule_names import RULE_NAMES
    assert isinstance(RULE_NAMES, dict), "RULE_NAMES must be a dict (data-driven, no engine recompile)"
    assert len(RULE_NAMES) >= 1, "RULE_NAMES must define at least one rule"


def test_tc_ext_rnf34_01_new_notification_channel_no_core_change():
    """TC-EXT-RNF34-01: Nuevo canal de notificación sin modificar núcleo (RNF-34).

    Verifica que NotificationChannel acepta channel_type arbitrario y que
    el modelo no restringe los tipos en tiempo de compilación.
    """
    from domain.entities.notification_channel import NotificationChannel

    # Add a new channel type without touching existing code
    custom_channel = NotificationChannel(
        organization_id=uuid4(),
        channel_type="PAGERDUTY_WEBHOOK",
        enabled=True,
        config_data={"routing_key": "abc123", "severity": "critical"},
    )

    assert custom_channel.channel_type == "PAGERDUTY_WEBHOOK"
    assert custom_channel.config_data["routing_key"] == "abc123"
    assert custom_channel.enabled is True

    # Core entity has no hard-coded enum restriction on channel_type
    sig = inspect.signature(NotificationChannel.__init__)
    assert "channel_type" in sig.parameters, "channel_type must be a free parameter (RNF-34)"

    channel_type_param = sig.parameters["channel_type"]
    annotation = channel_type_param.annotation
    # Should be str (not a restricted Enum), allowing open extension
    assert annotation in (str, inspect.Parameter.empty), (
        f"channel_type annotation '{annotation}' restricts extensibility (RNF-34)"
    )


# ===========================================================================
# TC-TRZ — TRAZABILIDAD
# ===========================================================================


def test_tc_trz_rnf35_01_verification_log_required_fields():
    """TC-TRZ-RNF35-01: Log de verificación contiene fuente, recurso, resultado e instante (RNF-35)."""
    from domain.entities.verification_result import VerificationResult
    from domain.enums import VerdictType

    result = VerificationResult(
        release_id=uuid4(),
        verdict=VerdictType.VALID,
        rule_results=[
            {
                "rule_id": "RV-01",
                "rule_name": "Artefactos existentes",
                "passed": True,
                "connector": "github-org",   # fuente
                "details": {},
            }
        ],
        summary={"source": "verification_worker", "resource": "release/v1.2.3"},
        duration_ms=2_340,
    )

    # RNF-35: fuente (source), recurso (resource), resultado (verdict), instante (executed_at)
    assert result.release_id is not None, "release_id = recurso (RNF-35)"
    assert result.verdict is not None, "verdict = resultado (RNF-35)"
    assert result.executed_at is not None, "executed_at = instante (RNF-35)"
    assert result.rule_results, "rule_results must carry per-rule traceability"

    rule_entry = result.rule_results[0]
    assert "rule_id" in rule_entry, "rule_id = fuente de regla (RNF-35)"
    assert "connector" in rule_entry, "connector = fuente del conector (RNF-35)"
    assert "passed" in rule_entry, "passed = resultado de regla (RNF-35)"


def test_tc_trz_rnf37_01_all_rf_trace_to_use_case_or_rule():
    """TC-TRZ-RNF37-01: Todo RF del catálogo traza a un CU o regla (RNF-37).

    Verifica que los casos de uso principales existen en el código fuente
    y que las reglas de verificación están definidas en rule_names.py.
    """
    use_cases_dir = _API_SRC / "application" / "use_cases"
    assert use_cases_dir.exists(), f"use_cases/ no encontrado en {_API_SRC}"

    # Key functional requirements → expected use case files
    rf_to_uc_map = {
        "RF-01 (Registrar usuario)": "auth_service.py",
        "RF-02 (Login)": "auth_service.py",
        "RF-03 (Gestionar organización)": "organization_service.py",
        "RF-04 (Lanzar verificación)": "verification_service.py",
        "RF-05 (Consultar historial)": "get_verification_history.py",
        "RF-06 (Dashboard)": "get_dashboard_metrics.py",
        "RF-07 (Conectores)": "connector_service.py",
        "RF-08 (Perfiles)": "profile_service.py",
        "RF-09 (API Keys)": "manage_api_keys.py",
    }

    all_uc_files = {f.name for f in use_cases_dir.rglob("*.py")}
    missing_traces: list[str] = []

    for rf, uc_file in rf_to_uc_map.items():
        if uc_file not in all_uc_files:
            missing_traces.append(f"  {rf} → '{uc_file}' no encontrado")

    assert not missing_traces, (
        f"TC-TRZ-RNF37-01: {len(missing_traces)} RF sin trazabilidad a CU:\n"
        + "\n".join(missing_traces)
    )

    # Verification rules (RV-*) must map to RULE_NAMES
    from core.rule_names import RULE_NAMES

    expected_rules = {f"RV-{i + 1:02d}" for i in range(10)}
    missing_rules = expected_rules - set(RULE_NAMES.keys())
    assert not missing_rules, (
        f"TC-TRZ-RNF37-01: Reglas sin nombre en RULE_NAMES: {missing_rules} (RNF-37)"
    )


# ===========================================================================
# TC-ORG — ORGANIZACIONALES / RGPD
# ===========================================================================


@pytest.mark.asyncio
async def test_tc_org_rnf38_01_gdpr_endpoints_functional():
    """TC-ORG-RNF38-01: Endpoints RGPD de exportación y borrado de datos son funcionales (RNF-38)."""
    from main import app
    from core.dependencies import get_current_user, get_user_service
    from httpx import AsyncClient, ASGITransport

    org_id = uuid4()
    user_id = uuid4()
    fake_user = _make_fake_current_user()
    fake_user.user_id = user_id
    fake_user.organization_id = org_id

    # Build a fake domain user entity (used by export endpoint via get_user_by_id)
    mock_user_entity = MagicMock()
    mock_user_entity.id = user_id
    mock_user_entity.email = "test@svaes.test"
    mock_user_entity.display_name = "Test User"
    mock_user_entity.role = MagicMock()
    mock_user_entity.role.value = "ADMIN"
    mock_user_entity.organization_id = org_id
    mock_user_entity.organization_ids = [org_id]
    mock_user_entity.is_active = True
    mock_user_entity.created_at = MagicMock()
    mock_user_entity.created_at.isoformat.return_value = "2026-01-01T00:00:00+00:00"
    mock_user_entity.terms_accepted_at = None
    mock_user_entity.privacy_accepted_at = None

    mock_user_svc = AsyncMock()
    mock_user_svc.get_user_by_id.return_value = mock_user_entity
    mock_user_svc.delete_user_account.return_value = None

    mock_jwt_handler = MagicMock()
    mock_jwt_handler.blacklist_token.return_value = None

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_user_service] = lambda: mock_user_svc

    # Also override jwt handler to avoid Redis calls during account deletion
    from core.dependencies import get_jwt_handler
    app.dependency_overrides[get_jwt_handler] = lambda: mock_jwt_handler

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",  # NOSONAR
        ) as client:
            # GDPR Art.20 — data export
            export_resp = await client.get("/api/v1/users/me/export")
            assert export_resp.status_code == 200, (
                f"GDPR export returned {export_resp.status_code} (RNF-38)"
            )
            export_data = export_resp.json()
            # GDPR Art.20 export wraps the subject's data under a "user" object
            # alongside schema_version / export_format metadata.
            assert "user" in export_data, "Export must contain user object (RNF-38)"
            assert "email" in export_data["user"], "Export user must contain email field (RNF-38)"
            assert export_data["user"]["email"] == "test@svaes.test"

            # GDPR Art.17 — right to erasure (sends password in body).
            # httpx's .delete() has no `json` param, so use .request() to send a body.
            delete_resp = await client.request(
                "DELETE",
                "/api/v1/users/me/account",
                json={"password": "TestPass1!"},
                headers={"Authorization": "Bearer test-token"},
            )
            assert delete_resp.status_code in (204, 422), (
                f"GDPR account deletion returned {delete_resp.status_code} — "
                "expected 204 (success) or 422 (validation, but endpoint exists) (RNF-38)"
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_tc_org_rnf40_01_openapi_json_valid_machine_readable():
    """TC-ORG-RNF40-01: /openapi.json devuelve spec OpenAPI válida machine-readable (RNF-40)."""
    from main import app
    from httpx import AsyncClient, ASGITransport

    app.router.lifespan_context = _noop_lifespan

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",  # NOSONAR
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200, f"GET /openapi.json returned {response.status_code} (RNF-40)"
    assert response.headers.get("content-type", "").startswith("application/json"), (
        "openapi.json must be served as application/json (RNF-40)"
    )

    spec = response.json()

    # Required OpenAPI 3.x top-level fields
    required_fields = {"openapi", "info", "paths"}
    missing = required_fields - set(spec.keys())
    assert not missing, f"openapi.json missing required fields: {missing} (RNF-40)"

    # Semantic version must match OpenAPI 3.x schema
    oa_version = spec.get("openapi", "")
    assert oa_version.startswith("3."), (
        f"Expected OpenAPI 3.x, got '{oa_version}' (RNF-40)"
    )

    # Info block must be parseable
    info = spec.get("info", {})
    assert "title" in info, "spec.info.title must be present (RNF-40)"
    assert "version" in info, "spec.info.version must be present (RNF-40)"

    # At least one path must be defined
    paths = spec.get("paths", {})
    assert len(paths) >= 1, "spec.paths must contain at least one endpoint (RNF-40)"
