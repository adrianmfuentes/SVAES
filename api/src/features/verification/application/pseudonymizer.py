import hashlib
from typing import Any, Dict, List, Set

PII_FIELD_PATTERNS: Set[str] = {
    "email",
    "emailaddress",
    "displayname",
    "name",
    "username",
    "assignee",
    "reporter",
    "creator",
    "author",
    "accountid",
    "user",
    "owner",
    "login",
    "fullname",
    "firstname",
    "lastname",
    "avatarurl",
    "profileurl",
    "url",
}

PII_VALUE_PREFIX = "sha256:"


def _is_pii_key(key: str) -> bool:
    return key.lower() in PII_FIELD_PATTERNS


def _hash_value(value: str) -> str:
    return PII_VALUE_PREFIX + hashlib.sha256(value.encode("utf-8")).hexdigest()


def pseudonymize(data: Any) -> Any:
    if isinstance(data, dict):
        result: Dict[str, Any] = {}
        for key, value in data.items():
            result[key] = pseudonymize(value)
            if _is_pii_key(key) and isinstance(value, str) and value:
                result[key] = _hash_value(value)
        return result
    if isinstance(data, list):
        return [pseudonymize(item) for item in data]
    return data
