# Plan de promoción a producción

**Referencia** [Especificación](spec.md)

1. Añadir la validación reutilizable. Comprobar el origen del PR y, en ambos eventos, el árbol de Git y los resultados de SonarCloud del commit exacto de main.
2. Activar el trigger en deploy, la cola de producción y las etiquetas de imagen por SHA. Conservar los inputs manuales y las migraciones.
3. Validar YAML, los flujos de promoción permitidos y rechazados y la interpolación de Docker Compose. Crear deploy desde el main anterior al disparador y aplicar su regla.
4. Integrar mediante PR a main y esperar su SonarCloud. Promover main a deploy por un segundo PR y observar el primer despliegue.
