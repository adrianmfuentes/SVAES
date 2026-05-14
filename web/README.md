# SVAES — Web Frontend

Frontend application for the **Automatic Software Delivery Verification System (SVAES)** built with **Angular**.

---

## Project structure

```
web/                            # Project root
├── src/
│   ├── app/
│   │   ├── core/             # Core modules (singleton services, guards, interceptors)
│   │   ├── shared/           # Shared components, directives, pipes
│   │   ├── features/        # Feature modules
│   │   ├── layouts/         # Layout components
│   │   └── app.config.ts    # Application configuration
│   ├── assets/               # Static assets
│   ├── styles/              # Global styles
│   └── environments/        # Environment configurations
├── public/                   # Public static files
├── package.json              # Dependencies
└── angular.json             # Angular CLI configuration
```

---

## Technologies

| Component | Technology | Version |
|---|---|---|
| Framework | Angular | 17+ |
| Language | TypeScript | 5.x |
| Package manager | npm | 10.x |
| Testing | Jasmine + Karma / Vitest | — |
| Styling | SCSS | — |

---

## Getting started

### Prerequisites

- Node.js 18+
- npm 10+

### Installation

```bash
cd web
npm install
```

### Development server

```bash
ng serve
```

Navigate to `http://localhost:4200/`. The application will automatically reload when source files change.

### Build

```bash
ng build
```

Build artifacts are stored in the `dist/` directory.

### Testing

```bash
# Unit tests
ng test

# E2E tests
ng e2e
```

---

## Additional resources

For more information about Angular CLI, visit [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli).
