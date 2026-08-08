"""Structured JSON logging without leaking credentials."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
thread_id_context: ContextVar[str | None] = ContextVar("thread_id", default=None)
user_id_context: ContextVar[str | None] = ContextVar("user_id", default=None)


class JsonFormatter(logging.Formatter):
    """Format logs as one JSON object per line."""

    _reserved = set(logging.makeLogRecord({}).__dict__)
    _redacted_keys = {"password", "password_hash", "token", "authorization", "api_key", "jwt"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
            "thread_id": thread_id_context.get(),
            "user_id": user_id_context.get(),
        }
        for key, value in record.__dict__.items():
            if key in self._reserved or key.startswith("_"):
                continue
            payload[key] = "[REDACTED]" if key.lower() in self._redacted_keys else value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger once with a JSON stream handler."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a named standard-library logger."""
    return logging.getLogger(name)

