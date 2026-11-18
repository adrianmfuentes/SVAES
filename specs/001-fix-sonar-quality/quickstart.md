# Verificación

1. En `web/`, ejecutar `pnpm exec ng test --watch=false --configuration=ci`.
2. En la raíz, ejecutar `uv run --frozen --no-build --project api --extra dev pytest tests/unit tests/acceptance/test_acceptance_structure.py`. Para integración y seguridad, usar PostgreSQL y Redis de prueba y los parámetros de `.github/workflows/sonar.yml`.
3. Verificar etiquetas y tipos de los campos de conectores. Comprobar en las vistas afectadas la visibilidad, las animaciones y los estados interactivos con y sin movimiento reducido.
4. Consultar el análisis del commit corregido. Comprobar el estado de los 67 avisos originales y la respuesta `OK` del Quality Gate.
