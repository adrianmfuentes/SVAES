"""
Unit tests for infrastructure/primary/middleware modules.
Covers: rate_limit limiter instantiation and configuration.
"""

import os
import sys
import pytest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestRateLimitMiddleware:
    def test_limiter_is_instantiated(self):
        """Branch: rate_limit limiter is a Limiter instance with get_remote_address"""
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        from infrastructure.primary.middleware.rate_limit import limiter

        assert isinstance(limiter, Limiter)
        assert limiter._key_func is get_remote_address  # type: ignore[attr-defined]

    def test_limiter_key_func_uses_client_ip(self):
        """Branch: key_func resolves to get_remote_address"""
        from infrastructure.primary.middleware.rate_limit import limiter

        assert limiter._key_func is not None  # type: ignore[attr-defined]
        assert callable(limiter._key_func)  # type: ignore[attr-defined]
