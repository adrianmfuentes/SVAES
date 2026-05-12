---
version: alpha
name: SVAES
description: >
  Sistema de Verificación Automática de Entregas de Software.
  Plataforma de administración técnica orientada a operadores y managers
  de equipos de software. La identidad visual prioriza la claridad del
  veredicto de verificación sobre cualquier otro elemento de la pantalla.
 
colors:
  primary: "#1E3A5F"
  on-primary: "#FFFFFF"
  secondary: "#2D6A4F"
  on-secondary: "#FFFFFF"
  tertiary: "#C0392B"
  on-tertiary: "#FFFFFF"
  neutral: "#F4F6F8"
  on-neutral: "#1A1A2E"
  surface: "#FFFFFF"
  on-surface: "#1A1A2E"
  border: "#D1D9E0"
  muted: "#6C757D"
  verdict-valid: "#2D6A4F"
  verdict-valid-bg: "#EAF5EE"
  verdict-warning: "#B8860B"
  verdict-warning-bg: "#FDF8E1"
  verdict-invalid: "#C0392B"
  verdict-invalid-bg: "#FDECEC"
  verdict-unevaluated: "#6C757D"
  verdict-unevaluated-bg: "#F0F0F0"

typography:
  h1:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.2
  h2:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.3
  h3:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.4
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 600
    letterSpacing: 0.05em
  mono:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.6

rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 10px 20px

  button-primary-hover:
    backgroundColor: "#16304F"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"

  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 10px 20px

  button-danger:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.md}"
    padding: 10px 20px

  badge-valid:
    backgroundColor: "{colors.verdict-valid-bg}"
    textColor: "{colors.verdict-valid}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  badge-warning:
    backgroundColor: "{colors.verdict-warning-bg}"
    textColor: "{colors.verdict-warning}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  badge-invalid:
    backgroundColor: "{colors.verdict-invalid-bg}"
    textColor: "{colors.verdict-invalid}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  badge-unevaluated:
    backgroundColor: "{colors.verdict-unevaluated-bg}"
    textColor: "{colors.verdict-unevaluated}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: 24px

  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: 10px 14px

  nav-item-active:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"

  nav-item:
    backgroundColor: transparent
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
---

## Overview

SVAES es una herramienta de trabajo para equipos técnicos, no una aplicación de
consumo. El diseño refleja esto: funcional, denso en información, sin ornamentos
innecesarios. La jerarquía visual está al servicio de una sola pregunta:
**¿es válida esta release?**

El veredicto de verificación es siempre el elemento más prominente de la pantalla.
Todo lo demás —navegación, filtros, metadatos— ocupa un plano secundario deliberado.

El lenguaje visual se inspira en los dashboards de herramientas de CI/CD y monitores
de infraestructura: alto contraste, tipografía legible en pantallas de bajo DPI,
colores semánticos con significado unívoco (verde = válido, rojo = inválido, siempre).

## Colors

La paleta combina un azul marino institucional con un verde de confirmación y un rojo
de alerta. El neutro cálido (`#F4F6F8`) actúa como fondo de la aplicación para
reducir la fatiga visual en sesiones largas.

- **Primary (`#1E3A5F`):** Azul marino. Barra lateral de navegación, botones
  principales, cabeceras de sección. Transmite fiabilidad e institucionalidad.

- **Secondary (`#2D6A4F`):** Verde bosque. Usado exclusivamente para el veredicto
  `VÁLIDA` y los estados de éxito. No debe emplearse para otros fines para preservar
  su significado semántico.

- **Tertiary (`#C0392B`):** Rojo señal. Reservado para el veredicto `NO_VÁLIDA`,
  errores de conector y acciones destructivas (botón «Rechazar release»).

- **Neutral (`#F4F6F8`):** Fondo de la aplicación y el menú lateral activo.
  Más suave que el blanco puro para entornos de trabajo prolongado.

- **Muted (`#6C757D`):** Metadatos secundarios, fechas, identificadores, texto de ayuda.
  Nunca para texto de acción o contenido operativo principal.

### Colores semánticos de veredicto

Los cuatro estados de verificación tienen colores fijos que no pueden reasignarse
a otros usos dentro de la interfaz:

| Estado | Color texto | Color fondo |
|---|---|---|
| VÁLIDA | `#2D6A4F` | `#EAF5EE` |
| CON_ADVERTENCIAS | `#B8860B` | `#FDF8E1` |
| NO_VÁLIDA | `#C0392B` | `#FDECEC` |
| NO_EVALUADA | `#6C757D` | `#F0F0F0` |

## Typography

Se usa **Inter** para toda la interfaz: fuente sans-serif diseñada específicamente
para legibilidad en pantalla a tamaños pequeños, con soporte completo de caracteres
latinos (tildes, eñes).

**JetBrains Mono** se usa exclusivamente para identificadores técnicos: UUIDs de
releases, referencias de commits, nombres de reglas (RV-01…RV-10), valores de
configuración JSONB y fragmentos de log. Nunca para texto de interfaz genérico.

La jerarquía tipográfica en la mayoría de vistas usa tres niveles: título de sección
(`h2`), nombre del elemento (`h3`) y datos operativos (`body-md` / `body-sm`).
Las etiquetas de tabla usan `label-caps` para distinguirlas del contenido sin
recurrir a la negrita.

## Layout

La aplicación usa un layout de dos columnas:

- **Barra lateral fija (240 px):** navegación principal con fondo `primary`.
  Texto de ítems en `on-primary` al 60 % de opacidad; ítem activo con fondo
  `neutral` y texto `primary`.

- **Área de contenido principal:** fondo `neutral`, contenedor central de máximo
  `1200 px` con padding de `spacing.xl` (32 px).

Las tarjetas (`card`) son la unidad de composición principal. Una vista típica
contiene una tarjeta de cabecera con el veredicto global y tarjetas secundarias
con el detalle regla a regla.

Los formularios usan cuadrícula de dos columnas en pantallas ≥ 1024 px y una columna
en móvil. Ancho máximo de campos de texto: `480 px`.

## Elevation & Depth

La interfaz es deliberadamente plana. Solo dos niveles de elevación:

- **Nivel 0:** fondo de la aplicación (`neutral`).
- **Nivel 1:** tarjetas y paneles (`surface`, `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`).

Los modales añaden un overlay `rgba(0,0,0,0.4)` sobre el contenido.
No se usan sombras pronunciadas ni efectos de profundidad adicionales.

## Shapes

- `rounded.sm` (4 px): badges, chips de filtro, etiquetas de estado.
- `rounded.md` (8 px): botones, inputs, tooltips.
- `rounded.lg` (12 px): tarjetas, paneles, modales.
- `rounded.full` (9999 px): badges de veredicto en modo compacto.

## Components

### Badges de veredicto

Son el componente más crítico de la interfaz. Siempre acompañan un icono y
nunca se usan sin él:

- ✅ `badge-valid` → VÁLIDA
- ⚠️ `badge-warning` → CON_ADVERTENCIAS
- ❌ `badge-invalid` → NO_VÁLIDA
- — `badge-unevaluated` → NO_EVALUADA

El sufijo `_CON_INCIDENCIAS` se renderiza como indicador secundario en `body-sm`
color `muted`, adyacente al badge principal, nunca dentro de él.

### Tabla de reglas de verificación

Columnas: identificador (`mono`), nombre (`body-md`), conector consultado
(`body-sm`), resultado (badge), evidencia (texto expandible en `body-sm`).
El identificador de regla usa siempre `mono` para facilitar la búsqueda visual.

### Inputs y formularios

- Estado normal: borde `1px solid {colors.border}`.
- Estado foco: borde `2px solid {colors.primary}`.
- Estado error: borde `{colors.tertiary}` + mensaje debajo en `body-sm` color `tertiary`.

Siempre hay una etiqueta visible (`label-caps`) encima del input.
No se usan placeholders como única indicación del campo.

Los estados de carga usan skeleton screens, no spinners bloqueantes,
porque las verificaciones son asíncronas y pueden tardar varios segundos.

## Do's and Don'ts

**Hacer:**
- Mostrar siempre el veredicto global en la parte superior de la vista de detalle
  de una release, antes de cualquier otro dato.
- Usar `mono` para todos los identificadores técnicos (UUIDs, RV-*, commits).
- Mantener los colores semánticos de veredicto consistentes en toda la aplicación.
- Usar skeleton screens para los estados de carga de resultados de verificación.

**No hacer:**
- No reutilizar el color `secondary` (verde) para nada que no sea el veredicto
  VÁLIDA o estados de éxito explícitos.
- No usar el color `tertiary` (rojo) para acciones destructivas rutinarias
  como «cancelar» o «volver»; solo para acciones irreversibles sobre la release.
- No truncar el campo de evidencia de una regla fallida: es el dato más importante
  cuando el usuario necesita depurar un resultado `NO_VÁLIDA`.
- No ocultar el sufijo `_CON_INCIDENCIAS` por razones estéticas.
