import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, organizations, projects, profiles, releases, connectors
from infrastructure.logging.logger import _configure_root_logger, get_logger

API_V1_PREFIX = "/api/v1"

_log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_root_logger()
    _log.info("SVAES API starting up")
    yield
    _log.info("SVAES API shutting down")


app = FastAPI(
    title="SVAES API",
    description="Sistema de Verificación Automática de Entregas de Software",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production via ALLOWED_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    _log.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(organizations.router, prefix=API_V1_PREFIX)
app.include_router(projects.router, prefix=API_V1_PREFIX)
app.include_router(profiles.router, prefix=API_V1_PREFIX)
app.include_router(releases.router, prefix=API_V1_PREFIX)
app.include_router(connectors.router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "message": "El backend está funcionando correctamente"}
