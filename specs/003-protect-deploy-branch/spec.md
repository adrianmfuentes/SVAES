# Rama protegida de despliegue

**Estado** Borrador para aprobación

## Objetivo

Crear `deploy` como rama de promoción a producción. Cada push recibido por `deploy`, incluida una fusión de PR, dispara el workflow **Deploy to Server**.

## Alcance

- Crear `deploy` a partir de `main`. Activar una regla de GitHub que exija PR, validación de la promoción y merge commit, y bloquee pushes directos, force-push y borrado, también para administradores.
- Promocionar mediante PR de `main` a `deploy`. La comprobación requerida verifica el origen del PR, el árbol que quedaría en `deploy` y el Quality Gate de SonarCloud para el commit de `main` correspondiente. El workflow de despliegue repite esa comprobación antes de publicar imágenes.
- Usar el entorno `production` para los pushes. Ejecutar las migraciones habituales y reservar el borrado de volúmenes para una ejecución manual que lo solicite expresamente.
- Serializar las promociones automáticas a producción para evitar que dos ejecuciones desplieguen al mismo tiempo.
- Actualizar los workflows y la guía de despliegue. Integrar los cambios en `main` y hacer la primera promoción con la protección activa.

## Fuera de alcance

Cambios de reglas de `main`, credenciales, servidores, configuración del entorno de producción y procedimiento manual existente.

## Criterios de aceptación

1. GitHub muestra `deploy` y una regla activa para esa rama que exige PR y comprobación de promoción. La regla bloquea force-push y borrado y aplica también a administradores.
2. Un push a `deploy` crea una ejecución de **Deploy to Server**. Los pushes a otras ramas quedan fuera del disparador automático.
3. Con SonarCloud `OK` para el código exacto promovido, la primera ejecución llega al despliegue de producción y registra su resultado. Si falta el análisis correspondiente, falla o el árbol difiere, la publicación de imágenes se bloquea.
4. El disparo automático nunca habilita la limpieza de volúmenes. La ejecución manual conserva los entornos e inputs existentes.

## Riesgos y supuestos

- El repositorio tiene un administrador. La protección exige un PR con comprobaciones, con cero aprobaciones obligatorias para permitir las promociones de ese mantenedor.
- El primer merge de promoción inicia un despliegue real a producción. La aprobación de esta especificación cubre esa activación y la integración de los workflows en `main`.
- Se usará el resultado de SonarCloud de `main` para el commit promovido. La comparación del árbol permite comprobar el contenido detrás del merge commit de `deploy`.
