# === STAGE 1: Build ===
# Multi-stage build con cargo-chef para cache optimo de dependencias

# Stage 1: Compilacion
FROM rust:bookworm AS chef

RUN cargo install cargo-chef

WORKDIR /app

# === STAGE 2: Planeacion de dependencias (cached) ===
FROM chef AS planner

COPY Cargo.toml Cargo.lock* ./
RUN cargo chef prepare --recipe-file recipe.json

# === STAGE 3: Build dependencias (cached) ===
FROM chef AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=planner /app/recipe.json .
RUN cargo chef cook --release --recipe-file recipe.json

COPY src ./src

RUN touch src/main.rs && cargo build --release

# === STAGE 4: Runtime ===
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    libssl3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 engine \
    && useradd --uid 1000 --gid engine --shell /bin/bash --create-home engine

WORKDIR /app

COPY --from=builder /app/target/release/svaes-engine /app/svaes-engine

RUN chown engine:engine /app/svaes-engine

RUN mkdir -p /var/log/svaes && chown engine:engine /var/log/svaes

USER engine

ENV ENGINE_HOST=0.0.0.0
ENV ENGINE_PORT=8081

EXPOSE 8081

HEALTHCHECK --interval=10s --timeout=3s --start-period=3s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

LABEL maintainer="SVAES Team"
LABEL description="SVAES Verification Engine - Stateless artifact verification motor"
LABEL version="1.0.0"

ENTRYPOINT ["/app/svaes-engine"]