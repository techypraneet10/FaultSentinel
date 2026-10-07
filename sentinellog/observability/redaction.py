"""Centralized secret and sensitive token redaction mechanism."""

import re
from typing import Any, Dict, List, Union

# Common credential patterns: Bearer tokens, API keys, passwords, secrets
_REDACTION_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.]{8,}['\"]?", re.IGNORECASE),
    re.compile(r"(?i)(secret\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.]{8,}['\"]?", re.IGNORECASE),
    re.compile(r"(?i)(password\s*[:=]\s*['\"]?)[^\s'\"]+['\"]?", re.IGNORECASE),
    re.compile(r"(?i)(authorization\s*[:=]\s*['\"]?)[^\s'\"]+['\"]?", re.IGNORECASE),
    re.compile(r"(?i)(token\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.]{8,}['\"]?", re.IGNORECASE),
]

_SENSITIVE_KEY_NAMES = {
    "api_key",
    "apikey",
    "secret",
    "password",
    "auth",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
}


def redact_string(value: str) -> str:
    """Scrub sensitive credential patterns from an arbitrary string."""
    if not isinstance(value, str):
        return value
    res = value
    for pattern in _REDACTION_PATTERNS:
        res = pattern.sub(r"\1[REDACTED]", res)
    return res


def redact_data(data: Any) -> Any:
    """Recursively redact dictionaries, lists, and strings."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if str(k).lower() in _SENSITIVE_KEY_NAMES:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(redact_data(item) for item in data)
    elif isinstance(data, str):
        return redact_string(data)
    return data
