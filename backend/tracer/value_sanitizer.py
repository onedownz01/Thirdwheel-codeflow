"""Runtime value sanitization for trace payloads and AI handoff."""
from __future__ import annotations

from ..models.schema import RuntimeValue

SENSITIVE_TOKENS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "key",
    "auth",
    "credential",
    "credit_card",
    "ssn",
    "pin",
    "cvv",
    "cookie",
}

MAX_STR_LEN = 160
MAX_LIST_LEN = 6
MAX_DICT_KEYS = 8



def sanitize_value(name: str, value) -> RuntimeValue:
    lowered = name.lower()
    is_sensitive = any(token in lowered for token in SENSITIVE_TOKENS)
    if is_sensitive:
        return RuntimeValue(name=name, value="••••••", type_name=type(value).__name__, is_sensitive=True)

    return RuntimeValue(
        name=name,
        value=_serialize(value),
        type_name=type(value).__name__,
        is_sensitive=False,
    )



def _serialize(value):
    try:
        if value is None:
            return "None"
        if isinstance(value, (bool, int, float)):
            return str(value)
        if isinstance(value, str):
            if len(value) > MAX_STR_LEN:
                return value[:MAX_STR_LEN] + "..."
            return value
        if isinstance(value, (list, tuple)):
            preview = [_serialize(v) for v in value[:MAX_LIST_LEN]]
            suffix = f" ... +{len(value) - MAX_LIST_LEN}" if len(value) > MAX_LIST_LEN else ""
            bracket_left, bracket_right = ("[", "]") if isinstance(value, list) else ("(", ")")
            return f"{bracket_left}{', '.join(preview)}{suffix}{bracket_right}"
        if isinstance(value, dict):
            keys = list(value.keys())[:MAX_DICT_KEYS]
            parts = []
            for k in keys:
                parts.append(f"{k}: {_serialize(value[k])}")
            suffix = f" ... +{len(value) - MAX_DICT_KEYS}" if len(value) > MAX_DICT_KEYS else ""
            return "{" + ", ".join(parts) + suffix + "}"
        return f"<{type(value).__name__}>"
    except Exception:
        return "<unserializable>"
