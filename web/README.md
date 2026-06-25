# SVAES — Web Frontend

> **TFG terminado** — Frontend application for the **Automatic Software Delivery Verification System (SVAES)**
> built with **Angular 21** (standalone components, zoneless).

---

## Docker access

When all services are started with `docker compose up`, the frontend is available at:

```
http://localhost:4200
```

(The `web` service runs `nginx:alpine` serving the built app on container port 80, mapped to host port 4200.)

---

## Project structure

```
web/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── api/              # Generated typed REST client (OpenAPI → TypeScript)
│   │   │   ├── guards/           # auth.guard.ts, role.guard.ts
│   │   │   ├── interceptors/     # jwt.interceptor.ts, error.interceptor.ts, timeout.interceptor.ts
│   │   │   ├── services/         # auth.service.ts, toast.service.ts
│   │   │   ├── i18n/             # TranslationService, TranslatePipe, locale JSON files
│   │   │   └── components/       # Shared components (toast, lang-toggle)
│   │   ├── features/
│   │   │   ├── auth/login/       # Login page (public)
│   │   │   ├── auth/activate/    # Account activation
│   │   │   ├── layout/shell/     # AppShell with sidebar + router-outlet
│   │   │   ├── dashboard/        # Full dashboard with charts, KPIs, recent releases
│   │   │   ├── releases/         # Full release management (list, detail, create)
│   │   │   ├── connectors/       # Full connector management (CRUD + test)
│   │   │   ├── profiles/         # Full profile management (CRUD + rules)
│   │   │   ├── admin/            # Global admin panel (orgs, users, access requests)
│   │   │   ├── profile/          # User profile with 2FA, password change
│   │   │   ├── projects/         # Project management
│   │   │   ├── logs/             # Audit log viewer
│   │   │   ├── landing/          # Public landing page
│   │   │   ├── legal/            # Legal pages (aviso-legal, privacidad)
│   │   │   ├── access-request/   # Access request form
│   │   │   ├── errors/           # Error pages (not-found, forbidden)
│   │   │   └── system/           # System status page
│   │   ├── app.config.ts         # Providers: HttpClient, interceptors, router, animations
│   │   ├── app.routes.ts         # Lazy-loaded route tree
│   │   └── app.ts                # Root component (<router-outlet>)
│   ├── index.html
│   ├── main.ts
│   └── styles.scss               # Material indigo-pink theme + global styles
├── public/                        # Static assets (favicon, etc.)
├── openapi.json                   # Cached OpenAPI 3.1 spec (generated from backend)
├── openapi-ts.config.ts           # Config for @hey-api/openapi-ts codegen
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
└── angular.json
```

---

## Technologies

| Component      | Technology              | Version      |
| -------------- | ----------------------- | ------------ |
| Framework      | Angular (standalone)    | 21.x         |
| Language       | TypeScript              | 5.9          |
| UI library     | Angular Material        | 21.x         |
| Package manager| pnpm                    | 10.x         |
| Styling        | SCSS                    | —            |
| Testing        | Vitest                  | 4.x          |
| API codegen    | @hey-api/openapi-ts     | 0.97         |

---

## Implemented features

| Feature                    | Status  | Details |
| -------------------------- | ------- | ------- |
| **Authentication**         | Done    | Login page at `/auth/login` with reactive form (email, password, organization selector). JWT stored in localStorage. |
| **JWT interceptor**        | Done    | Attaches `Authorization: Bearer <token>` to all outgoing requests. |
| **401 error interceptor**  | Done    | Clears token and redirects to `/auth/login` on 401 responses. |
| **AuthGuard**              | Done    | `CanActivateFn` — blocks unauthenticated access, redirects to login. |
| **RoleGuard**              | Done    | `CanActivateFn` — checks route `data.role` against the user's role. |
| **AppShell layout**        | Done    | Sidebar nav (Dashboard, Entregas, Conectores, Perfiles) + top bar with logout. |
| **REST client**            | Done    | Typed API client generated from the backend OpenAPI 3.1 spec (63 endpoints). |
| **Dashboard**              | Done    | Full dashboard with KPI cards, success rate chart, top failed rules, recent releases table. |
| **Releases / Entregas**    | Done    | Full release management: list with filters, create, detail view, artifact management. |
| **Connectors / Conectores**| Done    | Full connector management: list, create, test connection, edit, delete with form validation. |
| **Profiles / Perfiles**    | Done    | Full profile management: list, create, duplicate, update, delete, rule configuration. |
| **Admin panel**            | Done    | Global administration: organizations, users, access requests management. |
| **Projects**               | Done    | Project management with create/archive functionality. |
| **Audit logs**             | Done    | Audit log viewer with filtering. |
| **Profile settings**       | Done    | User profile with 2FA setup, password change, data export. |
| **i18n (ES/EN)**           | Done    | Full internationalization across all modules. |
| **Responsive design**      | Done    | Hamburger sidebar ≤1024px, horizontal table scroll, grid collapse at ≤768px across all components. |
| **Accessibility (WCAG 2.1 AA)** | Done | Skip links, ARIA roles/labels, `scope=col` on tables, `role=alert` on live regions, focus-visible, sr-only helpers, colour+text status indicators. |

---

## Getting started

### Prerequisites

- Node.js 18+
- pnpm 10+

### Install dependencies

```bash
cd web
pnpm install
```

### Development server

```bash
pnpm start
```

Navigate to `http://localhost:4200/`. The app proxies API calls to `http://localhost:8000` (the backend).

### Build for production

```bash
pnpm run build
```

Output goes to `dist/web/browser/`. Docker Compose serves this directory via nginx.

### Regenerate REST client

If the backend OpenAPI spec changes, regenerate the typed client:

```bash
# 1. Fetch the latest spec
cd ../api
$env:PYTHONPATH = "src"; uv run python -c "from main import app; import json; f=open('../web/openapi.json','w'); json.dump(app.openapi(),f,indent=2)"

# 2. Regenerate TypeScript types and SDK
cd ../web
pnpm exec openapi-ts
```

Output lands in `src/app/core/api/`.

### Run tests

```bash
pnpm test
```

---

## Auth flow

```
User → /auth/login → POST /api/v1/auth/login → JWT (access + refresh tokens)
                                                    ↓
                                          Stored in localStorage
                                                    ↓
                          JWT interceptor attaches Bearer token to every request
                                                    ↓
                          On 401 → 401 interceptor clears token → redirect to login
```

- **Public routes**: `/auth/login`, `/auth/register`, `/access-request`.
- **Protected routes**: Everything else — guarded by `AuthGuard`.
- **RBAC**: Role-based guards check route data for `role` (USER, MANAGER, ADMIN).

---

## Environment

| Variable          | Purpose                     | Default                  |
| ----------------- | --------------------------- | ------------------------ |
| `ALLOWED_ORIGINS` | CORS allowed origins (backend) | `http://localhost:4200` |
| —                 | Frontend proxies API calls via Angular dev server or nginx reverse proxy. |        |
