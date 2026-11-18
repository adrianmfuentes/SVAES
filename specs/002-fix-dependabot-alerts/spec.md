# Especificación de la remediación de Dependabot

**Estado** Borrador para aprobación

**Fecha** 2026-11-18

**Referencia** `origin/main` en `0cc2e5788c84826e0bcbfa26bd537b3207c45c0f`

## Objetivo y alcance

Resolver las 65 alertas que Dependabot tiene abiertas en SVAES. El inventario contiene 8 críticas, 32 altas, 24 medias y 1 baja. Hay 50 alertas en el lockfile de la API, 14 en el de la web y 1 en el pin de uv. [Dependabot](https://github.com/adrianmfuentes/SVAES/security/dependabot)

El trabajo incluye actualizar las dependencias afectadas y los componentes que las fijan. La alerta de uv corresponde a `.github/requirements/uv.txt`. SonarCloud y los dos Dockerfiles de la API también fijan versiones de uv inferiores a la corregida, por lo que se comprobarán y actualizarán en la misma remediación.

Quedan fuera de alcance las actualizaciones ajenas al inventario, los cambios de contrato de la aplicación, la desactivación de controles y el descarte manual de alertas.

## Inventario

Las versiones objetivo son los mínimos publicados que cubren las alertas agrupadas. Cualquier versión superior debe satisfacer los rangos, los requisitos de plataforma y los controles de instalación del proyecto.

| Paquete | Alertas | Versión del lockfile o pin | Mínimo corregido | Origen de la dependencia |
| --- | ---: | --- | --- | --- |
| Pillow | 43 | 12.3.0 | 13.0.0 | ReportLab |
| dnspython | 2 | 2.8.0 | 2.9.2 | email-validator |
| opentelemetry-api | 2 | 1.45.0 | 1.45.2 | FastAPI |
| Brotli | 1 | 1.2.0 | 1.2.1 | geventhttpclient |
| certifi | 1 | 2026.6.17 | 2026.10.18 | httpx, httpcore, requests y geventhttpclient |
| msgpack | 1 | 1.2.1 | 1.2.3 | Locust |
| Vite | 6 | 8.2.0 | 8.2.4 | Angular Build, Vitest y sus plugins |
| follow-redirects | 3 | 1.16.0 y 1.16.3 | 1.16.2 | http-proxy arrastra la copia afectada y axios usa la ya corregida |
| @vitest/mocker | 2 | 4.1.11 | 4.1.12 | Vitest |
| basic-ftp | 1 | 5.3.1 | 6.2.4 | get-uri |
| qs | 1 | 6.15.3 | 6.16.1 | body-parser |
| Zod | 1 | 4.4.2 y 4.6.6 | 4.6.6 | Angular Forms arrastra la copia afectada |
| uv | 1 | 0.11.15 | 0.13.4 | Pin de CI y requisitos. Los Dockerfiles usan 0.11.11 |

- **API** · #144–#170, #177–#191, #202–#204, #210, #213–#216.
- **Web** · #134, #137–#138, #141–#142, #172–#176, #193, #205–#206, #211.
- **uv** · #135.

Los tres archivos analizados coinciden con la referencia. Identificadores de blob de Git:

- `api/uv.lock` · `91c90e9074247938ec8fbcab7f0be4f156c8959e`
- `web/pnpm-lock.yaml` · `00674e30c9c7072fed95db125a2323c3b6c289e4`
- `.github/requirements/uv.txt` · `8df4b9f52b552a46ae01f09e1b77fe7cde0f1bf0`

## Escenarios y riesgos

1. **API** · La instalación reproducible conserva la compatibilidad declarada con Python 3.11+ y el entorno de CI y Docker en Python 3.13. Pillow cambia de versión mayor. Verificar exportaciones PDF y las suites existentes de API.
2. **Web** · El grafo resuelto elimina cada copia afectada. Verificar Angular, Vitest y el build con las versiones de Node y pnpm de CI y Docker. Mantener sincronizados los paquetes Vitest que comparten versión.
3. **Herramientas de build** · uv instala desde el lockfile en CI y en las imágenes de desarrollo y producción. Mantener verificación de hashes y comprobar la disponibilidad de las versiones para las plataformas soportadas.
4. **Dependencias transitivas de npm** · Revisar el rango de cada dependencia padre antes de imponer una versión. `get-uri` 8.0.2 declara `basic-ftp` ^6.2.4. Verificar que el gestor puede resolver esa actualización y que cumple los controles de publicación instalados.

## Criterios de aceptación

- **CA-001** · Comparar los grafos de dependencias antes y después. Ninguna de las copias resueltas entra en los rangos vulnerables de las 65 alertas.
- **CA-002** · Pasan las instalaciones bloqueadas de Python y pnpm, la suite de API con PostgreSQL y Redis, las pruebas y el build de Angular y la compilación de los Dockerfiles de la API.
- **CA-003** · CI y SonarCloud del commit publicado en `main` están en verde. El diff conserva los controles de instalación y se limita a las actualizaciones necesarias para la remediación.
- **CA-004** · Tras publicar en `main` y el recálculo de Dependabot, las 65 alertas originales aparecen como corregidas. Cualquier alerta que permanezca abierta se identifica por número y causa verificable.
