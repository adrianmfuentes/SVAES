from slowapi import Limiter
from slowapi.util import get_ipaddr

limiter = Limiter(key_func=get_ipaddr)

AUTH_RATE = "30/minute"
DEFAULT_RATE = "100/minute"
SEARCH_RATE = "30/minute"

def rate_limit_auth():
    return limiter.limit(AUTH_RATE)

def rate_limit_default():
    return limiter.limit(DEFAULT_RATE)

def rate_limit_search():
    return limiter.limit(SEARCH_RATE)