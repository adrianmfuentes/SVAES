# Contributing to SVAES

Thank you for your interest in contributing to SVAES.

## Branch Strategy

- `main` — stable, production-ready code
- `dev` — integration branch for features
- `feat/<name>` — new features
- `fix/<name>` — bug fixes

## Commit Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
feat(api): add new endpoint for connector management
fix(releases): resolve state transition race condition
docs(domain): clarify VerificationResult immutability
```

## Development Setup

```bash
# Clone the repository
git clone https://github.com/UO295454/SVAES.git
cd SVAES

# Backend
cd api
uv sync
uvicorn src.main:app --reload --port 8000

# Frontend
cd ../web
pnpm install
pnpm start          # dev server at http://localhost:4200
```

## Code Conventions

### Python (backend)

- Format: **Black** + **isort** (line length: 88)
- All functions must have type annotations
- Use **Pydantic v2** for data models
- Follow Clean Architecture: `domain/` has no external dependencies

### TypeScript (frontend)

- Format: **Prettier** + **ESLint** (angular-eslint)
- Standalone components (Angular 17+ style)
- i18n strings via `TranslatePipe` with keys in `web/src/assets/i18n/`
- Guards in `core/guards/`; API calls in `core/services/`

### Tests

- Unit tests are located in `tests/unit/`
- Follow the pattern: `test_<module>_<scenario>_<expected>`
- Do not mock domain entities or application commands

## Pull Request Process

1. Fork the repository and create a feature branch from `dev`
2. Ensure all tests pass: `pytest tests/unit/ -v`
3. Update documentation if applicable
4. Request review from a project maintainer
5. PRs merged to `main` require at least one approval

## Security Reports

Please see [SECURITY.md](./SECURITY.md) for how to report security vulnerabilities.

---

_Adrián Martínez (UO295454) — Universidad de Oviedo_
