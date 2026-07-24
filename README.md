[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)
[![Status](https://img.shields.io/badge/TFG-Finalizado-success)](https://github.com/adrianmfuentes/SVAES)
[![Deploy](https://img.shields.io/badge/Deploy-Producción-blue)](https://github.com/adrianmfuentes/SVAES)

**[English](README.en.md)** · **[Français](README.fr.md)**

# SVAES

## Sistema de Verificación Automática de Entregas de Software

Trabajo Fin de Grado — Grado en Ingeniería Informática del Software
Universidad de Oviedo · Curso 2025/2026 · Calificación: 10/10

Autor: Adrián Martínez Fuentes

---

## ¿Qué es SVAES?

Un **Quality Gate**: antes de dar una release por buena, SVAES comprueba automáticamente que sus artefactos (tareas, commits, documentos...) existen, están completos y son coherentes entre sí, tirando de las herramientas donde realmente viven esos datos (Jira, GitHub, Confluence...). El objetivo es quitar de en medio la checklist manual antes de cada entrega y dejar un rastro auditable de por qué una release se aprobó o no.

## Estado del proyecto

| Componente       | Estado |
| ---------------- | ------ |
| Backend (FastAPI)  | API REST completa, arquitectura hexagonal |
| Frontend (Angular) | SPA con auth, dashboard, releases, conectores, admin, i18n ES/EN/FR, 2FA |
| Motor (Rust)       | Evaluador paralelo con 10 reglas de negocio + reglas personalizadas |
| Conectores       | 20 implementaciones en 5 categorías funcionales |
| Despliegue       | Producción, Docker Compose + Oracle Cloud |

Documentación técnica completa (arquitectura, modelo de dominio, API, seguridad, despliegue): **[docs/](docs/README.md)**.

## Cómo funciona

1. Se crea una release en un proyecto y se le vinculan artefactos externos (tareas, commits, documentos...).
2. Un perfil de verificación define qué reglas aplicar y con qué severidad.
3. Al lanzar la verificación, el motor Rust recoge los datos vía conectores y evalúa las reglas en paralelo.
4. Se obtiene un veredicto global: **Válida**, **No válida** o **Con advertencias**.
5. El equipo consulta el detalle, exporta el informe (PDF/CSV) o consume la API directamente desde su pipeline CI/CD.

```text
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
                              ├──→ NO_VALIDA
                              └──→ CON_ADVERTENCIAS
                                        │
                                        ▼
                                   ARCHIVADA
```

## Puesta en marcha

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
# copia .env.example a .env y rellena JWT_SECRET_KEY y ENCRYPTION_KEY
docker compose up --build
```

API en `http://localhost:8000`, Swagger en `http://localhost:8000/docs`. Variables de entorno y despliegue en producción: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

### Ejecución sin Docker (desarrollo)

```bash
# Backend (api/)
cd api && uvicorn src.main:app --reload

# Frontend (web/)
cd web && npm install && npm start
```

Más detalle en [api/README.md](api/README.md) y [web/README.md](web/README.md).

## Feedback de usuarios

Los usuarios pueden enviar feedback (valoración 1-5 y comentario) desde un formulario en el footer de la landing page. Una GitHub Action programada ([`feedback-sync.yml`](.github/workflows/feedback-sync.yml)) sincroniza periódicamente el feedback recibido para que quede constancia pública:

<!-- FEEDBACK:START -->
> ★★★★★ "Honestamente es un sistema muy completo, con una estética cuidada y claramente con un gran trabajo detrás."
> — Javier Carrasco

> ★★★★★ "El sistema es muy robusto y que la interfaz esté en varios idiomas está genial. Al principio configurar las reglas desde cero cuesta un poco, pero luego funciona de maravilla"
> — Lara

> ★★★★★ "Interfaz muy intuitiva y visualmente bonita. Proyecto con gran ambición y de gran utilidad para el desarrollo general de software"
> — Daniel

> ★★★★★ "En general, la navegación es muy intuitiva y el atractivo de la web es sobresaliente, me encantan los colores escogidos y la tipografía. No obstante, he detectado durante mi tiempo de prueba con la aplicación algunos aspectos que considero…"
> — Vicente
<!-- FEEDBACK:END -->

---

_Última actualización: 30 de junio de 2026 — Adrián Martínez Fuentes (UO295454)_
