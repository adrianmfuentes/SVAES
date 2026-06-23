from slowapi import Limiter
from slowapi.util import get_ipaddr
from fastapi import Request
import hashlib

_API_KEY_HDR = "X-API-Key"


def _get_api_key_addr(request: Request) -> str:
    raw_key = request.headers.get(_API_KEY_HDR)
    if raw_key:
        return f"apikey:{hashlib.pbkdf2_hmac('sha256', raw_key.encode(), b'svk_api_key_pepper_v1', 100000).hex()}"
    return f"ip:{get_ipaddr(request)}"


limiter = Limiter(key_func=get_ipaddr)
api_key_limiter = Limiter(key_func=_get_api_key_addr)

AUTH_RATE = "30/minute"
DEFAULT_RATE = "100/minute"
SEARCH_RATE = "30/minute"
API_KEY_RATE = "100/minute"


def rate_limit_auth():
    return limiter.limit(AUTH_RATE)


def rate_limit_default():
    return limiter.limit(DEFAULT_RATE)


def rate_limit_search():
    return limiter.limit(SEARCH_RATE)


def rate_limit_api_key():
    return api_key_limiter.limit(API_KEY_RATE)