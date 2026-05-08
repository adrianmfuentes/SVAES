"""
Configuración compartida de pytest para la suite de pruebas unitarias.

Añade ``apps/api/src`` al ``sys.path`` para que los módulos del paquete
de la aplicación sean importables directamente por nombre (sin prefijos de
ruta) desde cualquier archivo de test dentro de ``tests/unit/``.
"""

import os
import sys
from pathlib import Path

# Must be set before any module imports infrastructure.database.session,
# which raises ValueError if DATABASE_URL is missing.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test_db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps" / "api" / "src"))
