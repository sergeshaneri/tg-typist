"""Structured stdlib logging helpers with conservative redaction."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any, TextIO
from urllib.parse import urlsplit, urlunsplit

REDACTED = "***"
CONTENT_REDACTED = "[redacted_content]"

_CONTENT_FIELD_NAMES = {
    "assistant_response",
    "content",
    "contents",
    "message",
    "messages",
    "prompt",
    "prompt_payload",
    "response",
    "text",
    "user_message",
}
_SECRET_FIELD_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
    "bot_token",
    "database_url",
    "db_url",
    "key",
    "password",
    "passwd",
    "secret",
    "token",
)
_DATABASE_URL_FIELD_PARTS = ("database_url", "db_url")


class StructuredLogger:
    """Small adapter that keeps stdlib logging while accepting key/value context."""

    def __init__(self, logger: logging.Logger, context: Mapping[str, Any] | None = None) -> None:
        self._logger = logger
        self._context = dict(context or {})

    def bind(self, **context: Any) -> StructuredLogger:
        """Return a logger with additional context applied to every log call."""

        return StructuredLogger(self._logger, {**self._context, **context})

    def debug(self, event: str, **context: Any) -> None:
        self._log(logging.DEBUG, event, context)

    def info(self, event: str, **context: Any) -> None:
        self._log(logging.INFO, event, context)

    def warning(self, event: str, **context: Any) -> None:
        self._log(logging.WARNING, event, context)

    def error(self, event: str, **context: Any) -> None:
        self._log(logging.ERROR, event, context)

    def exception(self, event: str, **context: Any) -> None:
        self._log(logging.ERROR, event, context, exc_info=True)

    def _log(
        self,
        level: int,
        event: str,
        context: Mapping[str, Any],
        *,
        exc_info: bool = False,
    ) -> None:
        if not self._logger.isEnabledFor(level):
            return

        structured = redact_context({**self._context, **context})
        self._logger.log(level, event, extra={"structured": structured}, exc_info=exc_info)


class StructuredFormatter(logging.Formatter):
    """Format log records as compact JSON objects with redacted structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        structured = getattr(record, "structured", None)
        if isinstance(structured, Mapping):
            payload.update(redact_context(structured))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def get_logger(name: str, **context: Any) -> StructuredLogger:
    """Return a structured logger backed by ``logging.getLogger``."""

    return StructuredLogger(logging.getLogger(name), context)


def configure_logging(level: str | int = logging.INFO, stream: TextIO | None = None) -> None:
    """Install the project JSON formatter on the root logger."""

    root_logger = logging.getLogger()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def redact_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of structured log context safe for default application logs."""

    return {key: redact_value(value, field_name=key) for key, value in context.items()}


def redact_value(value: Any, *, field_name: str | None = None) -> Any:
    """Redact secrets and full text-like payloads from a structured log value."""

    normalized_name = _normalize_field_name(field_name)
    if normalized_name in _CONTENT_FIELD_NAMES:
        return _redact_content_value(value)
    if _contains_any(normalized_name, _DATABASE_URL_FIELD_PARTS):
        return _redact_database_url(value)
    if _contains_any(normalized_name, _SECRET_FIELD_PARTS):
        return REDACTED if value is not None else None

    if isinstance(value, Mapping):
        return {
            str(nested_key): redact_value(nested_value, field_name=str(nested_key))
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)

    if isinstance(value, str):
        return _redact_secret_patterns(value)
    return value


def _redact_content_value(value: Any) -> str | None:
    if value is None:
        return None
    return CONTENT_REDACTED


def _redact_secret_patterns(value: str) -> str:
    if value.lower().startswith("bearer "):
        return "Bearer ***"
    return value


def _redact_database_url(value: Any) -> Any:
    if not isinstance(value, str):
        return REDACTED if value is not None else None

    parsed = urlsplit(value)
    if not parsed.scheme or parsed.password is None:
        return REDACTED

    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"

    username = parsed.username or ""
    netloc = f"{username}:***@{host}" if username else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _contains_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)


def _normalize_field_name(field_name: str | None) -> str:
    return (field_name or "").strip().lower().replace("-", "_")
