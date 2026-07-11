"""Structured JSON logging shared by all three services.

Includes a best-effort redaction layer for known sensitive field names and
PII-shaped substrings (constitution S-5). This is pattern matching, not a
guarantee: it cannot catch every possible shape of PII or secret. Callers
remain responsible for not logging raw sensitive payloads (student answers,
credentials, etc.) in the first place.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

SENSITIVE_KEYS = {"password", "token", "answer", "email"}
REDACTED = "***REDACTED***"

_EMAIL_RE = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+")
_BEARER_RE = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
_JWT_RE = re.compile(r"\b[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b")

_HANDLER_MARKER = "_platform_common_handler"


def _redact_text(text: str) -> str:
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _JWT_RE.sub(REDACTED, text)
    text = _EMAIL_RE.sub(REDACTED, text)
    return text


class RedactionFilter(logging.Filter):
    """Masks sensitive `extra=` fields by name and PII-shaped substrings
    (email addresses, bearer tokens/JWTs) in the rendered message."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__.keys()):
            if key.lower() in SENSITIVE_KEYS:
                setattr(record, key, REDACTED)

        record.msg = _redact_text(record.getMessage())
        record.args = ()
        return True


class JSONFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(service: str | None = None) -> None:
    """Install JSON-structured stdout logging with redaction on the root
    logger. Idempotent: safe to call more than once (e.g. under gunicorn
    worker forking or a Flask reload) -- reuses the existing handler instead
    of stacking duplicates."""
    service_name = service or os.environ.get("SERVICE_NAME", "unknown")
    root = logging.getLogger()

    handler = next(
        (h for h in root.handlers if getattr(h, _HANDLER_MARKER, False)),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler(stream=sys.stdout)
        setattr(handler, _HANDLER_MARKER, True)
        handler.addFilter(RedactionFilter())
        root.addHandler(handler)

    handler.setFormatter(JSONFormatter(service_name))
    root.setLevel(logging.INFO)
