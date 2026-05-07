# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.11.11 --only-binary :all: --require-hashes \
    --hash=sha256:d5b9f31dab557b5ee4257d8c6ba2608a63c7278537cb0cd102cf6fc518e3fb5c \
    --hash=sha256:1d227bb53b701e533f0aa074dd145a6fa31492dc7d6d57a6e72a700b9a4a1991 && \
    uv sync --frozen --no-dev --no-install-project --no-build

# ── Stage 2: production runtime ───────────────────────────────────────────────
FROM python:3.13-slim AS runtime

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
