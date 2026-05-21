import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))

API_BASE_URL = os.getenv("PERF_API_BASE_URL", "http://localhost:8000")
API_TOKEN = os.getenv("PERF_API_TOKEN", "")

TARGET_HOST = API_BASE_URL.rstrip("/")

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

if API_TOKEN:
    DEFAULT_HEADERS["Authorization"] = f"Bearer {API_TOKEN}"
