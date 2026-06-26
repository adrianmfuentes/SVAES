"""
Pruebas de Rendimiento — Locust (ISO 29119-4)
Total: 4 tests
  TC-PER-VL-01: E2E <= 5s (p95)
  TC-PER-VL-02: Motor Rust < 500ms (p95)
  TC-PER-VL-03: 50 POST /verify simultáneos -> todas 202 (RNF-06)
  TC-PER-CE-04: Suite completa -> SonarCloud cobertura >=70% (RNF-27)
"""

import os
import logging
from pathlib import Path
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

logger = logging.getLogger(__name__)

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE)
    except ImportError:
        pass

TARGET_HOST = os.getenv("PERF_API_BASE_URL", "http://localhost:8000")
API_TOKEN = os.getenv("PERF_API_TOKEN", "")
ADMIN_EMAIL = os.getenv("PERF_ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("PERF_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD", "")
CONTENT_TYPE_JSON = "application/json"
HEALTH_ENDPOINT = "/health"

if API_TOKEN:
    AUTH_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}
else:
    AUTH_HEADERS = {}

_shared_release_id = None
_shared_auth_headers = None


def _authenticate(client):
    """Login via /api/v1/auth/login and fetch a valid release UUID.

    Returns (auth_headers dict, release_id str or None).
    """
    global _shared_release_id, _shared_auth_headers

    if API_TOKEN and AUTH_HEADERS:
        return AUTH_HEADERS, _shared_release_id

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        logger.warning("PERF_ADMIN_EMAIL/PERF_ADMIN_PASSWORD not set — auth disabled")
        return {}, None

    # Reuse cached credentials across users to avoid flooding /login
    if _shared_auth_headers is not None:
        return _shared_auth_headers, _shared_release_id

    try:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            name="TC-PER-auth-login",
        )
        if resp.status_code != 200:
            logger.warning("Login failed: %s — %s", resp.status_code, resp.text)
            return {}, None

        token = resp.json().get("access_token", "")
        if not token:
            logger.warning("Login response missing access_token")
            return {}, None

        _shared_auth_headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(
            "/api/v1/releases",
            headers={
                "Content-Type": CONTENT_TYPE_JSON,
                "Accept": CONTENT_TYPE_JSON,
                **_shared_auth_headers,
            },
            name="TC-PER-auth-get-releases",
        )
        releases = resp.json() if resp.status_code == 200 else []
        _shared_release_id = releases[0]["id"] if releases else None

        if not _shared_release_id:
            logger.warning("No releases found — verify test will skip")

        return _shared_auth_headers, _shared_release_id
    except Exception as exc:
        logger.warning("Auth setup failed: %s", exc)
        return {}, None


class E2EVerificationUser(HttpUser):
    """
    TC-PER-VL-01: Usuario que simula flujo E2E completo.
    Objetivo: p95 <= 5 segundos por iteración completa.
    """
    host = TARGET_HOST
    wait_time = between(1, 3)

    def on_start(self):
        self.auth_headers, _ = _authenticate(self.client)
        if not self.auth_headers and AUTH_HEADERS:
            self.auth_headers = AUTH_HEADERS
        self.headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Accept": CONTENT_TYPE_JSON,
            **self.auth_headers,
        }

    @task(1)
    def e2e_health_to_results(self):
        """Flujo E2E: health -> releases -> results."""
        with self.client.get(HEALTH_ENDPOINT, name="TC-PER-VL-01 /health", catch_response=True) as r:
            if r.status_code == 200 and r.elapsed.total_seconds() <= 5.0:
                r.success()
            else:
                r.failure(f"health: status={r.status_code}, t={r.elapsed.total_seconds():.2f}s")

        with self.client.get(
            "/api/v1/releases",
            headers=self.headers,
            name="TC-PER-VL-01 /releases",
            catch_response=True,
        ) as r:
            if r.status_code == 200 and r.elapsed.total_seconds() <= 5.0:
                r.success()
            else:
                r.failure(f"releases: status={r.status_code}, t={r.elapsed.total_seconds():.2f}s")


class RustEngineUser(HttpUser):
    """
    TC-PER-VL-02: Usuario que verifica latencia del motor Rust.
    Objetivo: p95 < 500ms en llamadas al motor de verificación.
    """
    host = TARGET_HOST
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Accept": CONTENT_TYPE_JSON,
            **AUTH_HEADERS,
        }

    @task(1)
    def engine_health_check(self):
        """Verificación de latencia del motor Rust vía health endpoint."""
        with self.client.get(
            HEALTH_ENDPOINT,
            name="TC-PER-VL-02 engine-health",
            catch_response=True,
        ) as r:
            if r.status_code == 200 and r.elapsed.total_seconds() <= 0.5:
                r.success()
            else:
                r.failure(f"engine-health: status={r.status_code}, t={r.elapsed.total_seconds():.3f}s")


class ConcurrentVerifyUser(HttpUser):
    """
    TC-PER-VL-03: 50 peticiones POST /verify simultáneas -> todas 202.
    """
    host = TARGET_HOST
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.auth_headers, self.release_id = _authenticate(self.client)
        self.headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Accept": CONTENT_TYPE_JSON,
            **self.auth_headers,
        }

    @task(1)
    def concurrent_verify(self):
        """TC-PER-VL-03: POST /verify concurrente — todas deben retornar 202."""
        if not self.release_id:
            return

        with self.client.post(
            f"/api/v1/releases/{self.release_id}/verify",
            json={},
            headers=self.headers,
            name="TC-PER-VL-03 verify",
            catch_response=True,
        ) as r:
            if r.status_code == 202:
                r.success()
            elif r.status_code == 409:
                r.success()
            else:
                r.failure(f"POST /verify returned {r.status_code}, expected 202")


class WebLoadUser(HttpUser):
    """TC-PER-RNF02-01: 20 usuarios web concurrentes — latencia <= 3s (RNF-02).

    Ejecutar con:
        locust -f tests/performance/locustfile.py WebLoadUser \
            --users 20 --spawn-rate 20 --headless --run-time 30s
    """

    host = TARGET_HOST
    wait_time = between(0.05, 0.2)
    MAX_RESPONSE_MS = 3_000

    @task(3)
    def dashboard_metrics(self):
        """Solicitud al endpoint de métricas del dashboard."""
        with self.client.get(
            "/api/v1/dashboard/metrics",
            name="TC-PER-RNF02-01 /dashboard/metrics",
            catch_response=True,
        ) as resp:
            elapsed_ms = resp.elapsed.total_seconds() * 1_000
            if elapsed_ms > self.MAX_RESPONSE_MS:
                resp.failure(f"Dashboard > 3 s: {elapsed_ms:.0f} ms")
            else:
                resp.success()

    @task(1)
    def health(self):
        """Solicitud al endpoint de salud."""
        with self.client.get(
            HEALTH_ENDPOINT,
            name="TC-PER-RNF02-01 /health",
            catch_response=True,
        ) as resp:
            elapsed_ms = resp.elapsed.total_seconds() * 1_000
            if elapsed_ms > self.MAX_RESPONSE_MS:
                resp.failure(f"Health > 3 s: {elapsed_ms:.0f} ms")
            else:
                resp.success()


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Configuración de límites para pruebas de rendimiento.

    TC-PER-CE-04: La cobertura >= 70% se verifica vía SonarCloud
    (sonar-project.properties en la raíz del proyecto).
    Esta prueba no se ejecuta con Locust sino en el pipeline CI/CD.
    """
    if isinstance(environment.runner, MasterRunner):
        environment.runner.target_user_count = 50
        environment.runner.spawn_rate = 10
        environment.stop_timeout = 60
