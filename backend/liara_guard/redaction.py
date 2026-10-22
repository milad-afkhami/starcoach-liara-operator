"""Bounded redaction before persistence or model/browser presentation."""

import re

SENSITIVE = re.compile(r"(password|secret|token|authorization|api[-_]?key|cookie|credential|envs)", re.I)
ASSIGNMENT = re.compile(
    r"(?i)\b(password|secret|token|api[-_]?key|authorization|cookie)\b([\s:=]+)([^\s,;]+)"
)
BEARER = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def redact(value, secrets=(), depth=0):
    if depth > 8:
        return "[depth limited]"
    if isinstance(value, dict):
        return {
            str(k)[:100]: "[redacted]" if SENSITIVE.search(str(k)) else redact(v, secrets, depth + 1)
            for k, v in list(value.items())[:100]
        }
    if isinstance(value, list):
        return [redact(v, secrets, depth + 1) for v in value[:500]]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[redacted]")
        return ASSIGNMENT.sub(lambda m: m[1] + m[2] + "[redacted]", BEARER.sub("Bearer [redacted]", value))[
            :4000
        ]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return "[unsupported value]"
