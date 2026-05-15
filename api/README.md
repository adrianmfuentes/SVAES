# SVAES API

Backend FastAPI del sistema SVAES (Static Verification and Approval Engine System).

## Descripción

API RESTful para la gestión de organizaciones, proyectos, releases y verificación de artefactos. Implementa arquitectura hexagonal (Ports & Adapters) con autenticación JWT y control de acceso basado en roles (RBAC).

## Características

- Arquitectura hexagonal con puertos de entrada/salida
- Autenticación JWT con refresh tokens
- RBAC con 4 niveles de rol (U1-U4)
- Multi-tenancy con aislamiento por organización
- Rate limiting por endpoint
- Audit logging de operaciones

## Documentación

Documentación completa de la API: [docs/api/API_DOCUMENTATION.md](../docs/api/API_DOCUMENTATION.md)

Guías adicionales:
- [Testing](../docs/api/TESTING.md)
- [Deployment](../docs/api/DEPLOYMENT.md)
- [Postman](../docs/api/POSTMAN_GUIDE.md)

## Uso

```bash
cd api
uvicorn src.main:app --reload
```

## Endpoints Principales

| Router | Prefijo | Descripción |
|--------|---------|-------------|
| Auth | `/api/v1/auth` | Login, refresh tokens |
| Users | `/api/v1/users` | Perfil, gestión de usuarios |
| Organizations | `/api/v1/organizations` | Organizaciones y proyectos |
| Releases | `/api/v1/releases` | Gestión de releases |
| Connectors | `/api/v1/connectors` | Conectores externos |
| Profiles | `/api/v1/profiles` | Perfiles de verificación |
| Rules | `/api/v1/rules` | Reglas de verificación |
| Dashboard | `/api/v1/dashboard` | Métricas |