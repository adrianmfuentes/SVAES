# Verificación

1. Comparar cada versión resuelta en los dos lockfiles con los rangos de los 65 avisos.
2. Ejecutar las suites de API y Angular con las instalaciones congeladas del workflow de SonarCloud. Probar exportaciones y compilar producción web.
3. Construir las imágenes de API de producción y desarrollo. Verificar que los pins de uv y sus hashes corresponden a la publicación seleccionada.
4. Comprobar el análisis del commit publicado en `main` y los estados de los avisos originales cuando GitHub termine el recálculo.
