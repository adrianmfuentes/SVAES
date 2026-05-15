# === STAGE 1: Build ===
# Multi-stage build para optimizar el tamaño final de la imagen

# Stage 1: Compilacion
FROM rust:1.88-bookworm AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Cargo.toml Cargo.lock* ./

RUN mkdir -p src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src

COPY src ./src

RUN touch src/main.rs && cargo build --release

# === STAGE 2: Runtime ===
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

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

LABEL maintainer="SVAES Team"
LABEL description="SVAES Verification Engine - Stateless artifact verification motor"
LABEL version="1.0.0"

ENTRYPOINT ["/app/svaes-engine"]