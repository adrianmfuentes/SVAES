# Despliegue de SVAES - Guía de Producción

## Requisitos

| Componente | Versión mínima |
|------------|----------------|
| Python | 3.11+ |
| PostgreSQL | 16 |
| Redis | 7.x |
| Docker | 25.x |
| Docker Compose | 2.x |

## Variables de Entorno Obligatorias

### 1. Generar Secrets

Ejecutar el script de generación de secrets:

```bash
cd scripts
python generate_secrets.py
```

Esto generará valores para:

```env
# ── Auth ──────────────────────────────────────────────────────────────────────
# GENERADOS: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=<valor_generado>

# GENERADOS: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=<valor_generado>
```

### 2. Configuración de Base de Datos

```env
DATABASE_URL=postgresql+psycopg://svaes:<password>@host:5432/svaes
```

### 3. CORS (Producción)

```env
ALLOWED_ORIGINS=https://tu-dominio.com,https://app.tu-dominio.com
ENVIRONMENT=production
```

## Despliegue con Docker Compose

### docker-compose.yml (producción mínimo)

```yaml
services:
  api:
    build: ./apps/api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    depends_on:
      - postgres
      - redis
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

## Configuración de TLS/HTTPS

### Opción 1: Reverse Proxy (Nginx/Traefik)

```nginx
# /etc/nginx/sites-available/svaes
server {
    listen 443 ssl http2;
    server_name api.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
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

### Opción 2: Cloudflare/Nginx

Usar servicios de CDN/cloud para terminate TLS.

## Rate Limiting

El API aplica límites por defecto:

| Endpoint | Límite |
|----------|--------|
| `/api/v1/auth/login` | 30/minuto |
| `/api/v1/auth/refresh` | 30/minuto |
| Todos los demás | 100/minuto |

## Logs y Monitorización

### Formato de Logs

```
2026-05-13T10:30:00 | INFO     | audit | AUDIT | LOGIN_SUCCESS | user=abc123 | org=org456 | ...
2026-05-13T10:30:01 | INFO     | api.main | request_id=xyz-123 GET /api/v1/releases → 200 (12.5ms)
```

### Recommended: Enviar logs a

- **Desarrollo**: stdout (consola)
- **Producción**: Loggly, Datadog, CloudWatch, ELK stack

## Checklist de Producción

- [ ] `JWT_SECRET_KEY` generado con `secrets.token_urlsafe(32)`
- [ ] `ENCRYPTION_KEY` generado con `Fernet.generate_key()`
- [ ] `ENVIRONMENT=production` configurado
- [ ] `ALLOWED_ORIGINS` configurado con dominios reales
- [ ] TLS terminado (Nginx/reverse proxy o CDN)
- [ ] Rate limiting verificado
- [ ] Backup de PostgreSQL configurado
- [ ] Redis persistence habilitado
- [ ] Health check `/health` accesible
- [ ] Firewall configurado (solo puertos 80/443)

## Health Check

```bash
curl https://api.tu-dominio.com/health
# Respuesta: {"status": "ok", "service": "svaes-api", "version": "1.0.0"}
```

## Rollback

Si hay problemas tras actualizar:

```bash
docker-compose pull api
docker-compose up -d api
docker-compose logs -f api
```