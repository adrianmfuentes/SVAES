import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.rate_limit import limiter
from infrastructure.primary.routers.api.routers import (
    auth_router,
    organizations_router,
    releases_router,
    connectors_router,
    profiles_router,
    tasks_router,
    users_router,
    custom_roles_router,
    dashboard_router,
    api_keys_router,
    templates_router,
    notifications_router,
    admin_router,
)
from core.config import settings
from core.logger import _configure_root_logger, get_logger
from core.bootstrap import seed_admin_user

from domain.exceptions import (
    EntityNotFoundError,
    DomainException,
    ReleaseInvalidStateError,
    ConnectorConnectionFailedError,
)

API_V1_PREFIX = "/api/v1"
_log = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_root_logger()
    _log.info("Applying database migrations...")
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    _log.info("Database migrations applied")
    await seed_admin_user(settings)
    _log.info("SVAES API starting up (env=%s)", settings.environment)
    yield
    _log.info("SVAES API shutting down")


app = FastAPI(
    title="SVAES API",
    description="Automatic Software Delivery Verification System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

app.state.limiter = limiter
def _rate_limit_exceeded_handler_wrapper(request: Request, exc: Exception):
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler_wrapper)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Global domain exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(EntityNotFoundError)
async def _not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(ReleaseInvalidStateError)
async def _release_state_handler(request: Request, exc: ReleaseInvalidStateError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})

@app.exception_handler(ConnectorConnectionFailedError)
async def _connector_handler(request: Request, exc: ConnectorConnectionFailedError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(DomainException)
async def _domain_handler(request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    _log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if settings.is_production:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    duration_ms = (time.perf_counter() - start) * 1000
    _log.info(
        "request_id=%s %s %s → %d (%.1fms)",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(releases_router)
app.include_router(connectors_router)
app.include_router(profiles_router)
app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(custom_roles_router)
app.include_router(dashboard_router)
app.include_router(api_keys_router)
app.include_router(templates_router)
app.include_router(notifications_router)
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "svaes-api", "version": "1.0.0"}
