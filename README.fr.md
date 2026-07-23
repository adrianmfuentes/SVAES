[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)
[![Status](https://img.shields.io/badge/Mémoire-Terminé-success)](https://github.com/adrianmfuentes/SVAES)
[![Deploy](https://img.shields.io/badge/Déploiement-Production-blue)](https://github.com/adrianmfuentes/SVAES)

**[English](README.en.md)** · **[Español](README.md)**

# SVAES

## Système de Vérification Automatique des Livraisons de Logiciel

Mémoire de Fin de Licence — Terminé
Licence en Ingénierie Informatique du Logiciel, Université d'Oviedo · Année académique 2025/2026 · Note : 10/10

Auteur : Adrián Martínez Fuentes

---

## Qu'est-ce que SVAES ?

Un **Quality Gate** : avant de valider une release, SVAES vérifie automatiquement que ses artefacts (tâches, commits, documents...) existent, sont complets et cohérents entre eux, en interrogeant directement les outils où ces données vivent réellement (Jira, GitHub, Confluence...). L'objectif est de supprimer la checklist manuelle avant chaque livraison et de laisser une trace auditable des raisons d'approbation ou de rejet d'une release.

## État du projet

| Composant          | État |
| ------------------- | ---- |
| Backend (FastAPI)   | API REST complète, architecture hexagonale |
| Frontend (Angular)  | SPA avec auth, tableau de bord, releases, connecteurs, admin, i18n ES/EN/FR, 2FA |
| Moteur (Rust)       | Évaluateur parallèle avec 10 règles métier + règles personnalisées |
| Connecteurs         | 20 implémentations réparties en 5 catégories fonctionnelles |
| Déploiement         | Production, Docker Compose + Oracle Cloud |

Documentation technique complète (architecture, modèle de domaine, API, sécurité, déploiement) : **[docs/](docs/README.md)**.

## Fonctionnement

1. Une release est créée dans un projet et liée à des artefacts externes (tâches, commits, documents...).
2. Un profil de vérification définit les règles à appliquer et leur sévérité.
3. Au déclenchement, le moteur Rust récupère les données via les connecteurs configurés et évalue toutes les règles en parallèle.
4. Un verdict global est retourné : **Valide**, **Non valide** ou **Avec avertissements**.
5. L'équipe consulte le détail, exporte le rapport (PDF/CSV) ou utilise directement l'API depuis son pipeline CI/CD.

```text
BROUILLON → EN_ATTENTE → EN_VERIFICATION → VALIDE
                                ├──→ NON_VALIDE
                                └──→ AVEC_AVERTISSEMENTS
                                          │
                                          ▼
                                     ARCHIVEE
```

## Démarrage

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
# copiez .env.example vers .env et renseignez JWT_SECRET_KEY et ENCRYPTION_KEY
docker compose up --build
```

API sur `http://localhost:8000`, Swagger sur `http://localhost:8000/docs`. Variables d'environnement, déploiement en production et exécution sans Docker : **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## Avis des utilisateurs

Les utilisateurs peuvent envoyer un avis (note de 1 à 5 et commentaire) via un formulaire dans le pied de page de la landing page. Une GitHub Action planifiée ([`feedback-sync.yml`](.github/workflows/feedback-sync.yml)) synchronise périodiquement les avis reçus dans la section ci-dessous, comme preuve visible que le système a de vrais utilisateurs :

<!-- FEEDBACK:START -->
_Aucun avis publié pour le moment. Soyez le premier à partager votre opinion depuis la landing page._
<!-- FEEDBACK:END -->

Cette section n'est mise à jour automatiquement que dans le [README espagnol](README.md) ; cette copie traduite reflète la structure mais n'est pas resynchronisée à chaque exécution.

---

_Dernière mise à jour : 30 juin 2026 — Adrián Martínez Fuentes (UO295454)_
