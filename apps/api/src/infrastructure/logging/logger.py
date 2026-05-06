import logging
import sys
from functools import lru_cache

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"


def _configure_root_logger() -> None:
    """Sets up the root logger once. Called from the FastAPI lifespan."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Returns a module-level logger, creating it once and caching it.

    All loggers share the root handler configured by _configure_root_logger.
    """
    return logging.getLogger(name)
