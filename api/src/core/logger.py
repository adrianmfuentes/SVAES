import logging
import sys
from functools import lru_cache

"""
This module provides a centralized logging configuration and a factory function for obtaining loggers. The root logger is configured with 
a specific format and date format, and individual loggers can be retrieved by name using the get_logger function, which caches loggers. 
This setup ensures consistent logging across the application while allowing for modular loggers in different parts of the codebase.

Pattern used: Service Locator (for loggers) and Singleton (for root logger configuration).
"""

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"

def _configure_root_logger() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)

@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
