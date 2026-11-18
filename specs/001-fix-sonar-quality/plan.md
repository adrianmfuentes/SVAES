# Plan de implementación de SonarCloud

**Rama** `fix/sonar-quality` · **Especificación** [spec.md](spec.md)

## Contexto técnico

Angular, TypeScript y SCSS en `web/src/app`, Python 3.13 y FastAPI en `api/src`. Validación con Vitest, pytest y el workflow de SonarCloud.

## Constitución

Las correcciones preservan los contratos, los límites entre capas y los controles de seguridad. Se utilizan las dependencias y las suites existentes. Los cambios no requieren un modelo de datos ni contratos nuevos.

## Ejecución

Corregir primero conectores, operaciones asíncronas y ciclo de vida de la API. Ajustar después SVG, cascada, transiciones, movimiento y listas de exportación. Los [archivos por tarea](tasks.md), las [decisiones](research.md) y los [comandos de validación](quickstart.md) detallan cada paso.
