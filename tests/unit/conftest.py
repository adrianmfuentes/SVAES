"""
Shared pytest configuration for the unit test suite.

Adds ``apps/api/src`` to ``sys.path`` so application package modules are
importable by name (without path prefixes) from any test file under ``tests/unit/``.
"""

import os
import sys
from pathlib import Path

# Must be set before any module imports infrastructure.database.session,
# which raises ValueError if DATABASE_URL is missing.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test_db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps" / "api" / "src"))
