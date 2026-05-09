[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)

**[English](README.md)** · **[Español](README.md)**

# SVAES
## Système de Vérification Automatique des Livraisons de Logiciel

Travail de Fin de Licence
Licence en Ingénierie Informatique du Logiciel
Université d'Oviedo

Auteur: Adrián Martínez Fuentes
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

# 3. Portée fonctionnelle

Le système couvre les capacités suivantes:

- Gestion des organisations (multi-tenant)
- Gestion des projets et des releases
- Configuration des connecteurs externes
- Définition des profils de vérification
- Exécution automatique des vérifications
- Enregistrement des résultats et audit
- Exposition de l'API REST pour l'intégration

Hors scope:

- Exécution des pipelines CI/CD
- Modification des systèmes externes
- Analyse prédictive ou intelligence artificielle

---

# 4. Architecture du système

## 4.1 Approche architecturale

Le système adopte une architecture hybride basée sur:

- Architecture hexagonale (Ports & Adapters)
- Clean Architecture

Principe clé:

Les dépendances ne peuvent pointer que vers le domaine.

---

## 4.2 Décomposition en conteneurs

Le système est divisé en les composants suivants:

- Frontend (Angular SPA)
- Backend (FastAPI)
- Moteur de vérification (Rust)
- File de tâches (Celery + Redis)
- Base de données (PostgreSQL)
- Connecteurs externes

---

## 4.3 Flux d'exécution

1. L'utilisateur lance une vérification
2. Le backend valide l'état de la release
3. Une tâche est mise en file d'attente
4. Un worker traite la tâche
5. Les données sont récupérées via les connecteurs
6. Le moteur s'exécute
7. Le résultat est enregistré
8. Le frontend interroge l'état

---

# 5. Modèle de domaine

Entités principales:

- Organization
- Project
- Release
- Artifact
- VerificationProfile
- VerificationRule
- VerificationResult
- ConnectorInstance

Chaque vérification stocke un instantané complet de l'état évalué.

---

# 6. Cycle de vie d'une release

Le cycle de vie d'une release définit les états par lesquels passe une livraison de sa création jusqu'au résultat final de vérification.

```text
BORRADOR
   |
   v
PENDIENTE
   |
   v
EN_VERIFICACION
   |
   +--> VALIDA
   +--> NO_VALIDA
   +--> CON_ADVERTENCIAS
```

| État | Description |
| --- | --- |
| `BORRADOR` | Release créée, encore modifiable et non soumise pour vérification. |
| `PENDIENTE` | Release prête à être vérifiée. |
| `EN_VERIFICACION` | Vérification en cours par le worker. |
| `VALIDA` | Release vérifiée avec succès. |
| `NO_VALIDA` | Release rejetée pour non-conformité aux règles obligatoires. |
| `CON_ADVERTENCIAS` | Release acceptable, mais avec des problèmes non bloquants. |

États finals: `VALIDA`, `NO_VALIDA` et `CON_ADVERTENCIAS`.

---

# 7. Moteur de vérification

Implémenté en Rust.

Caractéristiques:

- Exécution parallèle
- Pas d'appels réseau
- Traitement en mémoire
- Résultat déterministe

Pipeline:

1. Validation
2. Évaluation des règles
3. Agrégation
4. Verdict

---

# 8. Connecteurs

Port principal:

IConnector

Permet d'intégrer des systèmes externes sans modifier le noyau.

---

# 9. Persistance

Base de données PostgreSQL:

- UUID comme identifiants
- JSONB pour les données dynamiques
- Intégrité référentielle
- Audit

---

# 10. Sécurité

| Couche | Mécanisme | Détail |
| --- | --- | --- |
| Authentification | JWT (HS256) | Tokens signés avec `PyJWT`. Claims: `sub`, `role`, `iat`, `exp` |
| Mots de passe | bcrypt (passlib) | Facteur de coût 12. Comparaison en temps constant |
| Credenciales conectores | Fernet (AES-128-CBC) | Chiffrement authentifié — échoue si le ciphertext est modifié |
| Endpoints protégés | Bearer token | `Authorization: Bearer <jwt>` requis sur tous les endpoints métier |
| Transactions | SQLAlchemy `session.begin()` | COMMIT automatique en succès, ROLLBACK automatique en exception |

### Flux d'authentification

```
POST /api/v1/auth/login
  body: { "email": "...", "password": "..." }
  → vérifie bcrypt contre hash en DB
  → retourne JWT

Requêtes protégées:
  header: Authorization: Bearer <JWT>
  → get_current_user valide signature + expiration
  → injecte l'entité User dans l'endpoint
  → 401 si token invalide ou expiré
```

---

# 11. Technologies

- Angular
- FastAPI
- Rust
- PostgreSQL
- Celery
- Redis
- Docker

---

# 12. Structure

```text
SVAES/
|-- apps/
|   |-- api/                         # API principale (FastAPI + Python)
|   |   |-- Dockerfile               # Multi-stage: builder → runtime
|   |   |-- pyproject.toml           # Dépendances Python
|   |   `-- src/
|   |       |-- main.py              # Point d'entrée FastAPI (CORS, lifespan, routers)
|   |       |-- api/
|   |       |   |-- dependencies.py  # Injection de dépendances et get_current_user
|   |       |   |-- routers/         # auth, organizations, projects, profiles, releases, connectors
|   |       |   `-- schemas/         # Modèles Pydantic request/response
|   |       |-- application/
|   |       |   `-- use_cases/       # Cas d'utilisation de l'application
|   |       |-- domain/
|   |       |   |-- entities/        # User, Organization, Release, ...
|   |       |   |-- ports/           # Interfaces: IUserRepository, IPasswordHasher, ...
|   |       |   `-- exceptions.py
|   |       `-- infrastructure/
|   |           |-- config.py        # Settings (pydantic-settings, .env)
|   |           |-- database/
|   |           |   |-- base.py
|   |           |   |-- session.py   # AsyncSession avec transactions automatiques
|   |           |   |-- models/      # Modèles SQLAlchemy
|   |           |   `-- repositories/
|   |           |-- security/
|   |           |   |-- password_hasher.py    # BcryptPasswordHasher
|   |           |   |-- jwt_handler.py        # JwtHandler (HS256)
|   |           |   |-- credential_encryptor.py # FernetCredentialEncryptor
|   |           |   `-- mock_task_queue.py
|   |           |-- adapters/
|   |           |   `-- connector_registry.py
|   |           `-- logging/
|   |               `-- logger.py    # Usine get_logger()
|   `-- web/                         # Application frontend
|       |-- public/
|       |-- src/
|       |   |-- app/
|       |   |-- components/
|       |   |-- features/
|       |   |-- hooks/
|       |   |-- pages/
|       |   |-- routes/
|       |   |-- services/
|       |   `-- styles/
|       `-- package.json
|-- docs/
|   |-- api/
|   |   `-- openapi.yaml
|   |-- database/
|   |   `-- erd.puml
|   |-- diagrams/
|   |   |-- exported/
|   |   `-- plantuml/
|   `-- tfg/
|-- packages/
|-- scripts/
|-- tests/
|-- workers/
|-- .env.example
|-- docker-compose.yml
|-- LICENSE
`-- README.md
```

---

# 13. Variables d'environnement

Copiez `.env.example` comme référence. Variables consommées par l'API Python:

| Variable | Description | Requise en prod |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/db` | Oui |
| `JWT_SECRET_KEY` | Clé de signature des tokens JWT | Oui |
| `JWT_ALGORITHM` | Algorithme JWT (défaut: `HS256`) | Non |
| `JWT_EXPIRE_MINUTES` | Expiration du token en minutes (défaut: `60`) | Non |
| `ENCRYPTION_KEY` | Clé Fernet pour le chiffrement des credentials | Oui |

Générer `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 14. API — Endpoints principaux

URL de base: `http://localhost:8000/api/v1`
Documentation interactive: `http://localhost:8000/docs`

| Méthode | Chemin | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Non | Login → retourne JWT |
| `POST` | `/organizations` | Oui | Créer organisation |
| `GET` | `/organizations` | Oui | Lister organisations |
| `POST` | `/projects` | Oui | Créer projet |
| `POST` | `/profiles` | Oui | Créer profil de vérification |
| `POST` | `/releases` | Oui | Créer release |
| `POST` | `/releases/{id}/verify` | Oui | Lancer vérification |
| `GET` | `/releases/{id}/results` | Oui | Obtenir résultats |
| `POST` | `/organizations/{id}/connectors` | Oui | Enregistrer connecteur |
| `GET` | `/health` | Non | Health check |

---

# 15. Exécution du système

## Développement local (avec Docker)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
docker compose up --build
```

Docker Compose charge automatiquement `docker-compose.yml` + `docker-compose.override.yml`:
- API à `http://localhost:8000` avec **hot reload** — les changements dans `src/` sont reflétés sans rebuild
- Swagger UI à `http://localhost:8000/docs`
- PostgreSQL exposé à `localhost:5432` (utilisateur: `svaes`, mot de passe: `svaes`, db: `svaes`)

## Développement local (sans Docker, uvicorn seulement)

```bash
# Démarrer seulement la base de données
docker compose up postgres -d

# Créer apps/api/src/.env avec:
# DATABASE_URL=postgresql+psycopg://svaes:svaes@localhost:5432/svaes
# JWT_SECRET_KEY=any-string

cd apps/api
pip install .
cd src
uvicorn main:app --reload
```

## Production (serveur)

```bash
# Exporter les variables réelles sur le serveur
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="long-random-secure-key"
export ENCRYPTION_KEY="$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Différences avec dev: pas de hot reload, pas de port postgres exposé, `restart: always`.

---

# 16. Conclusion

Le système fournit une solution découplée, extensible et robuste pour la vérification automatique des livraisons de logiciels.
