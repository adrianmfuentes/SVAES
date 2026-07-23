[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)
[![Status](https://img.shields.io/badge/Thesis-Completed-success)](https://github.com/adrianmfuentes/SVAES)
[![Deploy](https://img.shields.io/badge/Deploy-Production-blue)](https://github.com/adrianmfuentes/SVAES)

**[Español](README.md)** · **[Français](README.fr.md)**

# SVAES

## Automatic Software Delivery Verification System

Final Degree Project — Completed
Bachelor's Degree in Software Engineering, University of Oviedo · Academic Year 2025/2026 · Grade: 10/10

Author: Adrián Martínez Fuentes

---

## What is SVAES?

A **Quality Gate**: before a release is signed off, SVAES automatically checks that its artifacts (tasks, commits, documents...) exist, are complete, and are consistent with each other, pulling directly from the tools where that data actually lives (Jira, GitHub, Confluence...). The goal is to remove the manual pre-release checklist and leave an auditable trail of why a release was approved or rejected.

## Project status

| Component        | Status |
| ----------------- | ------ |
| Backend (FastAPI)  | Full REST API, hexagonal architecture |
| Frontend (Angular) | SPA with auth, dashboard, releases, connectors, admin, i18n ES/EN/FR, 2FA |
| Engine (Rust)      | Parallel evaluator with 10 business rules + custom rules |
| Connectors         | 20 implementations across 5 functional categories |
| Deployment         | Production, Docker Compose + Oracle Cloud |

Full technical documentation (architecture, domain model, API, security, deployment): **[docs/](docs/README.md)**.

## How it works

1. A release is created in a project and linked to external artifacts (tasks, commits, documents...).
2. A verification profile defines which rules to apply and at what severity.
3. On trigger, the Rust engine fetches artifact data through the configured connectors and evaluates all rules in parallel.
4. A global verdict comes back: **Valid**, **Invalid**, or **With warnings**.
5. The team reviews the detail, exports the report (PDF/CSV), or consumes the API directly from its CI/CD pipeline.

```text
DRAFT → PENDING → IN_VERIFICATION → VALID
                          ├──→ INVALID
                          └──→ WITH_WARNINGS
                                    │
                                    ▼
                               ARCHIVED
```

## Getting started

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
# copy .env.example to .env and fill in JWT_SECRET_KEY and ENCRYPTION_KEY
docker compose up --build
```

API at `http://localhost:8000`, Swagger at `http://localhost:8000/docs`. Environment variables, production deployment, and running without Docker: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## User feedback

Users can submit feedback (a 1-5 rating and a comment) through a form in the landing page footer. A scheduled GitHub Action ([`feedback-sync.yml`](.github/workflows/feedback-sync.yml)) periodically syncs the feedback received into the section below, as visible proof that the system has real users:

<!-- FEEDBACK:START -->
_No feedback published yet. Be the first to share your opinion from the landing page._
<!-- FEEDBACK:END -->

This section is kept up to date automatically only in the [Spanish README](README.md); this translated copy reflects the structure but is not re-synced on every run.

---

_Last updated: June 30, 2026 — Adrián Martínez Fuentes (UO295454)_
