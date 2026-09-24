"""Security sanitizers for redacting sensitive credentials and tokens."""

from __future__ import annotations

import re

# Precompiled regex patterns for sensitive credential redaction
_BEARER_PATTERN = re.compile(r"(?i)\b(bearer\s+)([a-zA-Z0-9_\-\.\~]{8,})")
_AUTH_HEADER_PATTERN = re.compile(
    r"(?i)\b(authorization\s*:\s*(?:bearer\s+|basic\s+)?)([^\s,;\"']{8,})"
)
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[-_]?key|access[-_]?token|auth[-_]?token|refresh[-_]?token|token|secret|password|client[-_]?secret)"
    r"(\s*[:=]\s*[\"']?)([^\s,\"';&]+)([\"']?)"
)
_URL_CREDENTIALS_PATTERN = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^:\s/]+):([^@\s/]+)@")


def sanitize_error_message(text: str | None) -> str | None:
    """Redact Authorization headers, Bearer tokens, API keys, passwords, and secrets.

    Ensures provider error strings or stack traces never leak credentials into
    database logs, telemetry, or API responses.
    """
    if text is None:
        return None

    sanitized = str(text)

    # 1. Redact Authorization headers
    sanitized = _AUTH_HEADER_PATTERN.sub(r"\1[REDACTED]", sanitized)

    # 2. Redact Bearer tokens
    sanitized = _BEARER_PATTERN.sub(r"\1[REDACTED]", sanitized)

    # 3. Redact Key-Value / JSON / Query parameter secrets
    def _redact_kv(match: re.Match) -> str:
        key = match.group(1)
        sep = match.group(2)
        val = match.group(3)
        quote = match.group(4)
        # Avoid redacting obvious non-secrets like 'none', 'null', 'false', 'true'
        if val.lower() in ("none", "null", "false", "true", "undefined"):
            return match.group(0)
        return f"{key}{sep}[REDACTED]{quote}"

    sanitized = _KEY_VALUE_SECRET_PATTERN.sub(_redact_kv, sanitized)

    # 4. Redact URL / DSN embedded credentials
    sanitized = _URL_CREDENTIALS_PATTERN.sub(r"\1[REDACTED]:[REDACTED]@", sanitized)

    return sanitized
