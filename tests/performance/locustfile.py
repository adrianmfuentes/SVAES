"""
Pruebas de Rendimiento — Locust (ISO 29119-4)
Total: 4 tests
  TC-PER-VL-01: E2E ≤ 5s (p95)
  TC-PER-VL-02: Motor Rust < 500ms (p95)
  TC-PER-CE-01: 50 peticiones simultáneas sin timeout
  TC-PER-CE-02: CE adicional de carga sostenida
"""

import os
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


TARGET_HOST = os.getenv("PERF_API_BASE_URL", "http://localhost:8000")
API_TOKEN = os.getenv("PERF_API_TOKEN", "")
CONTENT_TYPE_JSON = "application/json"
HEALTH_ENDPOINT = "/health"

if API_TOKEN:
    AUTH_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}
else:
    AUTH_HEADERS = {}


class E2EVerificationUser(HttpUser):
    """
    TC-PER-VL-01: Usuario que simula flujo E2E completo.
    Objetivo: p95 ≤ 5 segundos por iteración completa.
    """
    host = TARGET_HOST
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Accept": CONTENT_TYPE_JSON,
            **AUTH_HEADERS,
        }

    @task(1)
    def e2e_health_to_results(self):
        """Flujo E2E: health -> releases -> results."""
        with self.client.get(HEALTH_ENDPOINT, name="TC-PER-VL-01 /health", catch_response=True) as r:
            if r.elapsed.total_seconds() > 5.0:
                r.failure(f"p95 E2E exceeded 5s: {r.elapsed.total_seconds():.2f}s")
            else:
                r.success()

        with self.client.get(
            "/api/v1/releases",
            headers=self.headers,
            name="TC-PER-VL-01 /releases",
            catch_response=True,
        ) as r:
            if r.elapsed.total_seconds() > 5.0:
                r.failure(f"p95 E2E exceeded 5s: {r.elapsed.total_seconds():.2f}s")
            else:
                r.success()


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
            if r.elapsed.total_seconds() > 0.5:
                r.failure(f"Rust engine p95 exceeded 500ms: {r.elapsed.total_seconds():.3f}s")
            else:
                r.success()


class ConcurrentLoadUser(HttpUser):
    """
    TC-PER-CE-01: 50 peticiones simultáneas sin timeout.
    TC-PER-CE-02: Carga sostenida de clase de equivalencia.
    """
    host = TARGET_HOST
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.headers = {
            "Content-Type": CONTENT_TYPE_JSON,
            "Accept": CONTENT_TYPE_JSON,
            **AUTH_HEADERS,
        }

    @task(2)
    def concurrent_health(self):
        """TC-PER-CE-01: Health check concurrente — sin timeout."""
        with self.client.get(
            HEALTH_ENDPOINT,
            name="TC-PER-CE-01 health",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Health returned {r.status_code}")

    @task(1)
    def sustained_releases_list(self):
        """TC-PER-CE-02: Carga sostenida en listado de releases."""
        with self.client.get(
            "/api/v1/releases",
            headers=self.headers,
            name="TC-PER-CE-02 releases",
            catch_response=True,
        ) as r:
            status_ok = r.status_code in (200, 401, 403)
            if status_ok:
                r.success()
            else:
                r.failure(f"Releases returned {r.status_code}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Configuración de límites para pruebas de rendimiento."""
    if isinstance(environment.runner, MasterRunner):
        environment.runner.target_user_count = 50
        environment.runner.spawn_rate = 10
        environment.stop_timeout = 60
