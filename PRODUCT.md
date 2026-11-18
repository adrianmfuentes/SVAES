# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Equipos de desarrollo, QA y release managers que necesitan decidir si una release se puede publicar; integradores que consumen la API desde CI/CD. Segunda audiencia de esta landing: el tribunal y los lectores académicos del TFG/TFM (Universidad de Oviedo), que evalúan el proyecto desde la web pública.

## Product Purpose

SVAES (Sistema de Verificación Automática de Entregas de Software) es un Quality Gate: antes de dar una release por buena comprueba automáticamente que sus artefactos (tareas, commits, documentos) existen, están completos y son coherentes, consultando las herramientas donde viven los datos (Jira, GitHub, Confluence...). Deja un rastro auditable de por qué una release se aprobó o no. Éxito: eliminar la checklist manual previa a cada entrega.

## Positioning

Veredicto trazable y auditable (Válida / No válida / Con advertencias) con evidencias por regla, calculado por un motor Rust en paralelo, desde conectores a herramientas reales, autoalojable. La línea de investigación del TFM añade verificación semántica con modelos de lenguaje locales, sin enviar código ni requisitos a servicios externos.

## Operating Context

Flujo: crear release en un proyecto, vincular artefactos externos, perfil de verificación (reglas + severidad), lanzar verificación, consultar detalle, exportar PDF/CSV o consumir la API desde pipeline. Backend FastAPI (hexagonal), frontend Angular, motor Rust, 20 conectores en 5 categorías, despliegue Docker Compose en Oracle Cloud. UI en ES/EN (README en FR).

## Capabilities and Constraints

- 10 reglas de verificación (RV-01..RV-10) + reglas personalizadas; 20 conectores; 2FA TOTP; auditoría; RGPD; WCAG 2.1 AA en la app.
- La verificación semántica con LLM locales (TFM) NO está implementada en SVAES todavía: solo existe una prueba de concepto de viabilidad (12 modelos abiertos en Ollama sobre la GPU de la Escuela; 10 de 12 detectan el incumplimiento en el caso SEC-402). La landing debe presentarlo como línea de investigación en curso, no como funcionalidad entregada.
- No hay clientes, precios ni benchmarks de producción que citar. Plataforma de carácter académico, sin servicio comercial (aviso legal).
- Acceso por solicitud (`/request-access`) y login (`/auth/login`).
- Objetivo de accesibilidad de la landing: WCAG 2.2 AAA.

## Brand Commitments

Logo nuevo (2026-11-18): marco-puerta abierto + "S" en DM Serif Display; tinta #0D0F12, arena #E8D5A3, papel #F6F4F0; DM Serif Display (display), IBM Plex Sans/Mono. Assets en `web/public/images/logo/`. El TFG se conserva como histórico; el TFM lo extiende.

## Evidence on Hand

Resultados reales de la PoC en `D:\34644\Documents\Github\TFM-Investigacion` (tabla de 12 modelos con veredicto y tiempo). Demo pública en svaes.adrianmf.dev. Sin testimonios ni casos de cliente: no inventarlos.

## Product Principles

1. Veredicto explicable: toda conclusión muestra la regla, la fuente y la evidencia.
2. Honestidad sobre el estado: lo entregado y lo en investigación se distinguen visualmente.
3. Datos bajo control del usuario: autoalojable, IA local, nada sale a terceros.
4. Accesible por defecto, también para quien evalúa el proyecto.

## Accessibility & Inclusion

Estándar requerido para la landing: WCAG AAA (contraste 7:1, objetivos ≥44px, prefers-reduced-motion, sin dependencia solo del color, lenguaje claro).
