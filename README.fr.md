[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)

**[English](README.en.md)** · **[Español](README.md)**

# SVAES

## Système de Vérification Automatique des Livraisons de Logiciel

Travail de Fin de Licence
Licence en Ingénierie Informatique du Logiciel
Université d'Oviedo

Auteur: Adrián Martínez
Année académique: 2025/2026

---

# 1. Introduction

Le Système de Vérification Automatique des Livraisons de Logiciel (SVAES) est une plateforme conçue pour automatiser la validation des livraisons de logiciels dans les processus de développement modernes basés sur l'intégration continue.

Le système agit comme un mécanisme de Quality Gate, évaluant automatiquement la cohérence, l'intégrité et la complétude des artefacts associés à une release, par l'intégration avec plusieurs systèmes externes.

L'objectif principal est d'éliminer les processus de validation manuels, de réduire les erreurs humaines et de garantir une traçabilité complète du cycle de vie des livraisons.

---

# 2. Objectifs du système

## 2.1 Objectif général

Concevoir et implémenter un système extensible et découplé capable de vérifier automatiquement les livraisons de logiciels dans des environnements multi-outils.

## 2.2 Objectifs spécifiques

- Automatiser la validation des releases
- Garantir une traçabilité complète des vérifications
- S'intégrer avec des outils externes sans couplage fort
- Fournir des métriques et une observabilité du processus de qualité
- Permettre son utilisation comme Quality Gate dans les pipelines CI/CD

---

# 3. État du projet

| Composant        | État           |
| ---------------- | ---------------- |
| Backend FastAPI  | API REST complète avec tous les endpoints                 |
| Frontend Angular | SPA avec authentification, dashboard, releases, connecteurs, profil, admin, i18n ES/EN, 2FA |
| Moteur Rust      | Moteur complet dans engine/, évaluateur parallèle + 10 règles |
| Worker Celery    | Worker réel dans verification_worker.py                     |
| Connecteurs      | 20 connecteurs dans 5 catégories fonctionnelles                 |

---

# 4. Portée fonctionnelle

Le système couvre les capacités suivantes :

- Gestion des organisations (multi-tenant)
- Gestion des projets et des releases
- **Configuration des connecteurs externes (20 implémentations)**
- Définition des profils de vérification
- Exécution automatique des vérifications
- Enregistrement des résultats et audit
- Exposition de l'API REST pour l'intégration

Hors scope :

- Exécution des pipelines CI/CD
- Modification des systèmes externes
- Analyse prédictive ou intelligence artificielle

---

# 5. Architecture du système

## 5.1 Approche architecturale

Le système adopte une architecture hybride basée sur :

- Architecture hexagonale (Ports & Adapters)
- Clean Architecture

Principe clé :

> Les dépendances ne peuvent pointer que vers le domaine.

## 5.2 Décomposition en conteneurs

Le système est divisé en les composants suivants :

- Frontend (Angular SPA)
- Backend (FastAPI)
- Moteur de vérification (Rust)
- File de tâches (Celery + Redis)
- Base de données (PostgreSQL)
- Connecteurs externes

## 5.3 Structure du backend

```
api/src/
├── domain/                    # Entités, enums, exceptions
│   ├── entities/              # User, Organization, Project, Release, Artifact, ConnectorInstance
│   └── enums.py               # UserRole, ConnectorType, ConnectorImplementation, etc.
│
├── application/               # Cas d'utilisation (logique métier)
│   ├── ports/
│   │   ├── input/             # IReleaseService, IConnectorService, etc.
│   │   └── output/            # IUserRepository, IConnectorRegistry, IConnector
│   └── use_cases/             # Implémentations des cas d'utilisation
│
├── infrastructure/            # Adaptateurs
│   ├── primary/
│   │   ├── routers/           # Endpoints FastAPI (v1)
│   │   └── middleware/         # JWT, rate limiting, password hasher
│   └── secondary/
│       ├── database/          # Modèles SQLAlchemy + dépôts
│       ├── queue/             # Celery + Redis
│       └── connectors/         # Implémentations des connecteurs
│           ├── task_management/   # Jira, Linear, Trello, Asana
│           ├── source_control/    # GitHub, GitLab, Bitbucket, Gitea
│           ├── documentation/       # Confluence, Notion, Wiki.js, BookStack
│           ├── planning/           # ClickUp, Taiga, Plane, Miro
│           └── change_management/  # Jira SM, GLPI, Zammad, Redmine
│
└── core/                      # Config, dépendances, rate limiting
```

---

# 6. Système de connecteurs

## 6.1 Architecture à deux niveaux

Le système de connecteurs suit une conception à **deux niveaux** :

| Concept                     | Description                | Exemples                                             |
| --------------------------- | -------------------------- | ---------------------------------------------------- |
| **ConnectorType**           | Type fonctionnel générique | `GESTOR_TAREAS`, `REPO_CODIGO`, `SISTEMA_DOCUMENTAL` |
| **ConnectorImplementation** | Implémentation concrète    | `JIRA`, `GITHUB`, `CONFLUENCE`, `LINEAR`             |

Un manager configure dans son organisation quelles implémentations concrètes il souhaite utiliser pour chaque type fonctionnel.

## 6.2 Types fonctionnels disponibles

| Type                        | Description                                                                    |
| --------------------------- | ------------------------------------------------------------------------------ |
| `GESTOR_TAREAS`             | Outils qui suivent le travail quotidien, les histoires utilisateur et les bugs |
| `REPO_CODIGO`               | Source de vérité pour les branches, commits et tags de version                 |
| `SISTEMA_DOCUMENTAL`        | Rapports de tests, manuels techniques et plans de livraison                    |
| `HERRAMIENTA_PLANIFICACION` | Roadmap à long terme, épics et plans de release                                |
| `GESTION_CAMBIOS`           | Systèmes ITSM pour approbations formelles, CABs et incidents de production     |

---

# 7. Modèle de domaine

Entités principales :

- **Organization** — Tenant principal avec owner
- **User** — Utilisateur avec rôle et organisation
- **Project** — Appartient à une org, a un profil de vérification
- **Release** — Version de logiciel avec état et artefacts
- **Artifact** — Référence externe liée à une release
- **ConnectorInstance** — Configuration d'un connecteur dans une org
- **VerificationProfile** — Ensemble de règles pour un projet
- **VerificationRule** — Modèle avec sévérité et paramètres
- **VerificationResult** — Résultat de vérification avec verdict

---

# 8. Cycle de vie d'une release

```text
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
    │           │              │
    │           └──────────────┴──→ NO_VALIDA
    │                               │
    └───────────────────────────────┴──→ CON_ADVERTENCIAS
    │
    └──────────────────────────────────→ ARCHIVADA
```

| État               | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `BORRADOR`         | Release créée, encore modifiable et non soumise pour vérification. |
| `PENDIENTE`        | Release prête à être vérifiée.                                     |
| `EN_VERIFICACION`  | Vérification en cours par le worker.                               |
| `VALIDA`           | Release vérifiée avec succès.                                      |
| `NO_VALIDA`        | Release rejetée pour non-conformité aux règles obligatoires.       |
| `CON_ADVERTENCIAS` | Release acceptable, mais avec des problèmes non bloquants.         |

---

# 9. Persistance

Base de données PostgreSQL :

- UUID comme identifiants
- JSONB pour les données dynamiques
- Intégrité référentielle
- Piste d'audit

---

# 10. Sécurité

| Couche                  | Mécanisme                    | Détail                                             |
| ----------------------- | ---------------------------- | -------------------------------------------------- |
| Authentification        | JWT (HS256)                  | Tokens signés. Claims: `sub`, `role`, `iat`, `exp` |
| Double facteur (2FA)    | TOTP (pyotp + segno)         | Authentification à deux étapes optionnelle par utilisateur |
| Mots de passe           | bcrypt (passlib)             | Facteur de coût 12. Comparaison en temps constant  |
| Credentials connecteurs | Fernet (AES-128-CBC)         | Chiffrement authentifié                            |
| Endpoints protégés      | Bearer token                 | `Authorization: Bearer <jwt>` requis               |
| Isolation multi-tenant  | Filtre par `organization_id` | 403 sur accès croisé                               |
| Rate limiting           | slowapi                      | 30 req/min auth, 100 req/min lectures, 20 req/min écritures |
| Force brute             | Verrouillage de compte       | 5 tentatives échouées → 15 min de blocage          |
| Audit RGPD              | audit_log (PostgreSQL)       | Traçabilité complète ; pseudonymisation dans les vérifications |

---

# 11. Technologies

| Couche                 | Technologie              |
| ---------------------- | ------------------------ |
| API Backend            | FastAPI (Python 3.11+)   |
| Base de données        | PostgreSQL 16            |
| ORM                    | SQLAlchemy 2.x           |
| Migrations             | Alembic                  |
| Authentification       | JWT (PyJWT)              |
| Client HTTP            | httpx (async)            |
| Frontend               | Angular 21               |
| Moteur de vérification | Rust (Actix-web + Rayon) |
| File de tâches         | Celery + Redis           |
| Conteneurs             | Docker + Docker Compose  |

---

# 12. Variables d'environnement

| Variable             | Description                                    | Requise |
| -------------------- | ---------------------------------------------- | ------- |
| `DATABASE_URL`       | `postgresql+asyncpg://user:pass@host:5432/db`  | Oui     |
| `JWT_SECRET_KEY`     | Clé de signature des tokens JWT                | Oui     |
| `JWT_ALGORITHM`      | Algorithme JWT (défaut : `HS256`)              | Non     |
| `JWT_EXPIRE_MINUTES` | Expiration du token en minutes (défaut : `60`) | Non     |
| `ENCRYPTION_KEY`     | Clé Fernet pour le chiffrement des credentials | Oui     |
| `ENVIRONMENT`        | `development` ou `production`                  | Non     |
| `ALLOWED_ORIGINS`    | Origines CORS séparées par virgule             | Non     |

Générer `ENCRYPTION_KEY` :

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 13. API — Endpoints principaux

URL de base : `http://localhost:8000/api/v1`
Documentation interactive : `http://localhost:8000/docs`

### Authentification

| Méthode | Chemin                 | Auth | Description                                 |
| ------- | ---------------------- | ---- | ------------------------------------------- |
| `POST`  | `/auth/login`          | Non  | Login → retourne JWT (étape 1 si 2FA actif) |
| `POST`  | `/auth/2fa/verify`     | Non  | Vérifier code TOTP (étape 2)                |
| `POST`  | `/auth/refresh`        | Non  | Rafraîchir token                            |
| `POST`  | `/auth/register`       | Non  | Inscription avec acceptation des conditions |

### Organisations

| Méthode | Chemin                               | Auth     | Description            |
| ------- | ------------------------------------ | -------- | ---------------------- |
| `GET`   | `/organizations`                     | ADMIN    | Lister toutes          |
| `POST`  | `/organizations`                     | ADMIN    | Créer                  |
| `GET`   | `/organizations/{org_id}/connectors` | MANAGER+ | Lister connecteurs     |
| `POST`  | `/organizations/{org_id}/connectors` | MANAGER+ | Enregistrer connecteur |

### Releases et vérifications

| Méthode | Chemin                    | Auth      | Description          |
| ------- | ------------------------- | --------- | -------------------- |
| `POST`  | `/projects/{id}/releases` | OPERATOR+ | Créer release        |
| `POST`  | `/releases/{id}/verify`   | OPERATOR+ | Lancer vérification  |
| `GET`   | `/releases/{id}/results`  | OPERATOR+ | Historique résultats |

### Connecteurs

| Méthode | Chemin                  | Auth             | Description                     |
| ------- | ----------------------- | ---------------- | ------------------------------- |
| `GET`   | `/connectors/types`     | Tout utilisateur | Lister types et implémentations |
| `POST`  | `/connectors/{id}/test` | MANAGER+         | Tester connexion                |

---

# 14. Exécution du système

## Développement local (avec Docker)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
docker compose up --build
```

API : `http://localhost:8000` · Swagger : `http://localhost:8000/docs` · PostgreSQL : `localhost:5432`

## Développement local (sans Docker)

```bash
# Seulement la base de données
docker compose up postgres -d

cd api
pip install -e .
uvicorn src.main:app --reload --port 8000
```

## Production

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="clé-longue-aléatoire-sécurisée"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

# 15. Conclusion

Le système fournit une solution découplée, extensible et robuste pour la vérification automatique des livraisons de logiciels.

Le système est pleinement opérationnel avec :

- 20 implémentations de connecteurs dans 5 types fonctionnels
- Frontend Angular avec authentification 2FA, dashboard, gestion des releases et connecteurs
- Internationalisation ES/EN dans tous les modules frontend
- Isolation multi-tenant complète avec piste d'audit RGPD
- RBAC avec rôles prédéfinis et personnalisés

---

_Dernière mise à jour : Juin 2026 — Adrián Martínez (UO295454)_
