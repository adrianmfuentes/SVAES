import time
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.rate_limit import limiter
from api.routers import auth, organizations, projects, profiles, releases, connectors, artifacts, verification_rules
from api.routers import users
from domain.exceptions import (
    EntityNotFoundError,
    DomainException,
    ReleaseInvalidStateError,
    ConnectorConnectionFailedError,
)
from api.src.core.config import settings
from api.src.infrastructure.secondary.database.session import get_db_session
from api.src.core.logging.logger import _configure_root_logger, get_logger

API_V1_PREFIX = "/api/v1"

_log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_root_logger()
    _log.info("Applying database migrations...")
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
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
async def _rate_limit_exceeded_handler_wrapper(request: Request, exc: Exception):
    return await _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler_wrapper)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(artifacts.router, prefix=API_V1_PREFIX)
app.include_router(connectors.router, prefix=API_V1_PREFIX)
app.include_router(verification_rules.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health():
    db_ok = False
    redis_ok = False

    try:
        from api.src.infrastructure.secondary.database.session import _get_engine
        engine_factory = _get_engine()
        async with engine_factory() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        _log.warning("Health check: database unreachable")

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        _log.warning("Health check: Redis unreachable")

    overall = "ok" if (db_ok and redis_ok) else "degraded"
    payload = {
        "status": overall,
        "db": "reachable" if db_ok else "unreachable",
        "redis": "reachable" if redis_ok else "unreachable",
    }
    return JSONResponse(
        status_code=200 if overall == "ok" else 503,
        content=payload,
    )
