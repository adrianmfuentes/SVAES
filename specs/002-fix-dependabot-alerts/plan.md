# Plan de remediación de Dependabot

**Rama** `main`, autorizada por el usuario. **Base** `0cc2e57`. [Especificación](spec.md)

## Contexto y constitución

Python 3.11+ con uv y Docker en 3.13. Angular con pnpm y Node 22 en CI y Docker. Conservar el alcance, las instalaciones congeladas, la comprobación de hashes y los controles de publicación. Los cambios no afectan al modelo de datos, puertos ni contratos.

## Ejecución

1. Regenerar `api/uv.lock` con actualizaciones selectivas de los seis paquetes afectados.
2. Corregir las copias npm y sincronizar el conjunto Vitest usando `web/package.json`, `web/pnpm-workspace.yaml` y `web/pnpm-lock.yaml`.
3. Actualizar los pins de uv y los hashes correspondientes en CI y Docker.
4. Comparar los grafos, ejecutar las verificaciones y publicar en `main`.
