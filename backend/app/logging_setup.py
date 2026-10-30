"""Structured JSON logging with correlation IDs."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record to JSON.

        Args:
            record: Standard library log record.

        Returns:
            JSON string including optional correlation and billing fields.
        """
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        cid = correlation_id_var.get()
        if cid:
            payload["correlation_id"] = cid
        for key in (
            "event_id",
            "organization_id",
            "invoice_id",
            "payment_attempt_id",
            "outbox_id",
            "customer_id",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger for stdout JSON logging.

    Args:
        level: Logging level name (for example ``INFO`` or ``DEBUG``).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        Standard library ``Logger`` instance.
    """
    return logging.getLogger(name)
