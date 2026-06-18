# SVAES Deployment - Production Guide

## Requirements

| Component | Minimum Version |
|------------|----------------|
| Python | 3.11+ |
| PostgreSQL | 16 |
| Redis | 7.x |
| Rust | 1.77+ (for engine builds) |
| Docker | 25.x |
| Docker Compose | 2.x |

## Required Environment Variables

### 1. Generate Secrets

Run the secret generation script:

```bash
cd scripts
python generate_secrets.py
```

This will generate values for:

```env
# ── Auth ──────────────────────────────────────────────────────────────────────
# GENERATED: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=<generated_value>

# GENERATED: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=<generated_value>
```

### 2. Database Configuration

```env
DATABASE_URL=postgresql+psycopg://svaes:<password>@host:5432/svaes
```

### 3. CORS (Production)

```env
ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com
ENVIRONMENT=production
```

## Deployment with Docker Compose

### Minimum Services

```yaml
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - ENGINE_URL=http://engine:8081
    depends_on:
      - postgres
      - redis
      - engine
    restart: unless-stopped

  engine:
    build: ./engine
    ports:
      - "8081:8081"
    environment:
      - ENGINE_HOST=0.0.0.0
      - ENGINE_PORT=8081
    restart: unless-stopped

  worker:
    build: ./api
    command: celery -A src.infrastructure.secondary.queue.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - ENGINE_URL=http://engine:8081
    depends_on:
      - postgres
      - redis
      - engine
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=svaes
      - POSTGRES_USER=svaes
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  pgdata:
```

### Option 1: Reverse Proxy (Nginx/Traefik)

```nginx
# /etc/nginx/sites-available/svaes
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 2: Cloudflare/Nginx

Use CDN/cloud services to terminate TLS.

## Rate Limiting

The API applies default limits:

| Endpoint | Limit |
|----------|--------|
| `/api/v1/auth/login` | 30/minute |
| `/api/v1/auth/refresh` | 30/minute |
| All others | 100/minute |

## Logging and Monitoring

### Log Format

```
2026-05-13T10:30:00 | INFO     | audit | AUDIT | LOGIN_SUCCESS | user=abc123 | org=org456 | ...
2026-05-13T10:30:01 | INFO     | api.main | request_id=xyz-123 GET /api/v1/releases → 200 (12.5ms)
```

### Recommended: Send logs to

- **Development**: stdout (console)
- **Production**: Loggly, Datadog, CloudWatch, ELK stack

## Production Checklist

- [ ] `JWT_SECRET_KEY` generated with `secrets.token_urlsafe(32)`
- [ ] `ENCRYPTION_KEY` generated with `Fernet.generate_key()`
- [ ] `ENVIRONMENT=production` configured
- [ ] `ALLOWED_ORIGINS` configured with real domains
- [ ] `ENGINE_URL` configured pointing to the engine service
- [ ] TLS terminated (Nginx/reverse proxy or CDN)
- [ ] Rate limiting verified
- [ ] PostgreSQL backup configured
- [ ] Redis persistence enabled
- [ ] API `/health` health check accessible
- [ ] Engine `/health` health check accessible
- [ ] Celery worker started and connected to Redis
- [ ] Firewall configured (ports 80/443 only)

## Health Check

```bash
# API
curl https://api.your-domain.com/health
# Response: {"status": "ok", "service": "svaes-api", "version": "1.0.0"}

# Engine
curl http://engine:8081/health
# Response: {"status": "healthy", "service": "svaes-engine", "version": "1.0.0"}
```

## Rollback

If issues arise after updating:

```bash
docker-compose pull api
docker-compose up -d api
docker-compose logs -f api
```
