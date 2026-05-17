# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN pip install uv==0.11.11 && uv sync --frozen --no-install-project --no-build

# ── Stage 2: production runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/alembic/ /app/alembic/
COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
