"""
Shared pytest configuration for the unit test suite.

Adds ``apps/api/src`` to ``sys.path`` so application package modules are
importable by name (without path prefixes) from any test file under ``tests/unit/``.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test_db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault(
    "ENCRYPTION_KEY", "ZOFHEQsSkoUeaU4Orkdn165PjxO-27Xg8YSQSynK-fM="
)
os.environ.setdefault(
    "ALLOWED_ORIGINS", '["http://localhost:4200","http://localhost:3000"]'
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps" / "api" / "src"))
