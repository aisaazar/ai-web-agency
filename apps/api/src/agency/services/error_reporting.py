"""Structured production error reporting with a provider seam."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger("agency.errors")


@dataclass(frozen=True)
class ErrorEvent:
    request_id: str
    method: str
    path: str
    status_code: int
    error_type: str
    message_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "request_id": self.request_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "error_type": self.error_type,
            "message_fingerprint": self.message_fingerprint,
        }


def report_exception(
    exc: Exception,
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int = 500,
) -> ErrorEvent:
    """Emit a safe structured event without logging exception text or request data."""
    message_fingerprint = hashlib.sha256(str(exc).encode("utf-8", "replace")).hexdigest()
    event = ErrorEvent(
        request_id=request_id,
        method=method,
        path=path,
        status_code=status_code,
        error_type=type(exc).__name__,
        message_fingerprint=message_fingerprint,
    )
    logger.error("unhandled_exception %s", json.dumps(event.as_dict(), sort_keys=True))
    return event
