# SVAES Constitution

> SVAES continúa como proyecto vivo hacia el TFM. La documentación del TFG se conserva
> como histórico. Este texto no define requisitos del TFM ni políticas académicas.

## Core Principles

### I. Dependencias hacia dentro
`domain/` MUST NOT importar de `application/` ni de `infrastructure/`, y MUST NOT realizar
llamadas de red. Todo cambio que viole esta regla MUST rechazarse.
Fuente: docs/development/guidelines.md §4.1 (L89-91), §8 (L167).

### II. Núcleo genérico
El núcleo MUST NOT acoplarse a ninguna herramienta externa concreta. Toda integración se
hace implementando el puerto `IConnector`. Los nombres de herramientas (Jira, GitLab,
Confluence…) MUST NOT codificarse fuera de `infrastructure/adapters/`, y los casos de uso
MUST NOT instanciar conectores concretos.
Fuente: guidelines.md §4.2 (L93-94), §8 (L168-170).

### III. Aislamiento multi-tenant y RBAC
Todos los repositorios y casos de uso MUST filtrar por `organization_id`, y no se genera
código que acceda a datos de otra organización. Todo endpoint nuevo MUST respetar los
guards de rol correspondientes.
Fuente: guidelines.md §4.4-4.5 (L101-105), §8 (L171); SECURITY.md L26-28, L98.

### IV. Veredictos inmutables y motor acotado
`verification_result` MUST NOT ser mutable tras su creación. El motor de verificación
(`engine/`) se comunica con el backend por HTTP y MUST NOT incluir acceso a BD ni lógica de
conectores.
Fuente: guidelines.md §4.3 (L96-99), §8 (L172).

### V. Evidencia mediante pruebas
Las pruebas se escriben en la capa que corresponde. Las entidades de dominio y los comandos
de aplicación MUST NOT mockearse; solo se mockean adaptadores de infraestructura
(repositorios, conectores, cola). Los objetivos de cobertura documentados conservan su
fuerza original y se consultan en su fuente, no se reproducen aquí.
Fuente: docs/development/testing.md L46-48, L58-66; CONTRIBUTING.md L56-61;
guidelines.md §5 (L117).

### VI. Secretos y datos personales
Los secretos MUST gestionarse por variables de entorno y MUST NOT versionarse (`.env` fuera
de git). Los controles listados en la tabla «Implemented Security Controls» de SECURITY.md
(cifrado de credenciales, pseudonimización, registro de auditoría, límite de intentos,
etc.) son la línea base de seguridad vigente del proyecto.
Fuente: SECURITY.md L91-109; .gitignore L16-19.

## Comprobaciones y convenciones vigentes

**Comprobaciones que el CI ya ejecuta** (.github/workflows/sonar.yml L50-113, deploy.yml
L43-50, codeql.yml L9, L21): pruebas Python (unitarias, integración, seguridad, estructura
de aceptación) con cobertura; pruebas de la SPA; cobertura del motor Rust; análisis
SonarCloud en push y PR; CodeQL (Python y JavaScript/TypeScript); y el despliegue se
bloquea si el último workflow de Sonar no tuvo éxito.

**Convenciones documentadas** (guidelines.md §5, CONTRIBUTING.md): conservan la fuerza que
ya tienen en esos documentos, con independencia de que el CI las compruebe. No se
reproducen ni se refuerzan aquí.

**Cambios que requieren confirmación explícita** del desarrollador (guidelines.md §7,
L155-161): esquema de BD, interfaz HTTP backend-motor, nuevas dependencias, renombrado o
eliminación de puertos y lógica de agregación de veredictos.

## Flujo de desarrollo

El trabajo nuevo usa los artefactos de Spec Kit (`.specify/` y la ubicación de specs y
planes que Spec Kit defina), sin crear un árbol paralelo. La documentación existente
(docs/development/, docs/security/, memoria del TFG) se conserva y no se migra. Las reglas
operativas para agentes siguen en docs/development/guidelines.md §6-8.

## Governance

- **Precedencia:** esta constitución prevalece sobre specs y planes. Un conflicto se
  resuelve enmendando la constitución o corrigiendo el artefacto, no ignorándolo.
- **Enmiendas:** se documentan en un cambio revisable, con motivo y versión semántica
  (MAJOR: principio eliminado o redefinido; MINOR: principio o sección nuevos o ampliados;
  PATCH: aclaraciones).
- **Revisión:** los planes y PRs relevantes indican si respetan los principios; las
  desviaciones se justifican por escrito.

**Version**: 1.0.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25
