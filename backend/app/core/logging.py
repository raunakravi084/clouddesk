"""JSON logging with `request_id` and `workflow_id` on every line (CLAUDE.md §16).

The ids live in context variables so they follow a request or workflow across
`await` boundaries. Middleware and the workflow service set them; nothing else
needs to pass them around.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
workflow_id_var: ContextVar[str | None] = ContextVar("workflow_id", default=None)

# Attributes every LogRecord has; anything else was passed via `extra=` and is emitted.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "workflow_id": workflow_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _RESERVED and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class _StdoutHandler(logging.StreamHandler):
    """Writes to the current `sys.stdout`, so later redirection (pytest, uvicorn) is honoured."""

    @property
    def stream(self):  # type: ignore[override]
        return sys.stdout

    @stream.setter
    def stream(self, _value) -> None:
        pass


def setup_logging(level: str | int | None = None) -> None:
    """Install a single JSON handler on the root logger. Safe to call more than once."""
    if level is None:
        from app.core.config import get_settings

        level = get_settings().log_level

    handler = _StdoutHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper() if isinstance(level, str) else level)

    # Route uvicorn through the root JSON handler instead of its own formatters.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
