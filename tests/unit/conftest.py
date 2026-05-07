"""
Configuración compartida de pytest para la suite de pruebas unitarias.

Añade ``apps/api/src`` al ``sys.path`` para que los módulos del paquete
de la aplicación sean importables directamente por nombre (sin prefijos de
ruta) desde cualquier archivo de test dentro de ``tests/unit/``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps" / "api" / "src"))
