import pytest
from slowapi import Limiter
from infrastructure.primary.middleware.rate_limit import limiter

pytestmark = pytest.mark.unit


class TestRateLimiter:
    def test_limiter_is_instance(self):
        assert isinstance(limiter, Limiter)

    def test_limiter_has_key_func(self):
        from slowapi.util import get_remote_address
        assert limiter._key_func is get_remote_address
