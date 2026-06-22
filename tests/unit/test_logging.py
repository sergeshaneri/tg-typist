from __future__ import annotations

import importlib
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any, cast

from _pytest.logging import LogCaptureFixture

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

logging_module = importlib.import_module("tg_typist.logging")
CONTENT_REDACTED = logging_module.CONTENT_REDACTED
REDACTED = logging_module.REDACTED
StructuredFormatter = logging_module.StructuredFormatter
get_logger = logging_module.get_logger
redact_context = logging_module.redact_context


def test_redacts_secret_fields_and_database_url_password() -> None:
    context = redact_context(
        {
            "telegram_bot_token": "123456:telegram-secret-token",
            "deepseek_api_key": "deepseek-secret-key",
            "database_url": "postgresql+asyncpg://db_user:db_password@db.example.com:5432/db",
            "headers": {"Authorization": "Bearer deepseek-secret-key"},
        }
    )

    rendered = f"{context}"

    assert context["telegram_bot_token"] == REDACTED
    assert context["deepseek_api_key"] == REDACTED
    assert context["database_url"] == "postgresql+asyncpg://db_user:***@db.example.com:5432/db"
    assert context["headers"] == {"Authorization": REDACTED}
    assert "telegram-secret-token" not in rendered
    assert "deepseek-secret-key" not in rendered
    assert "db_password" not in rendered
    assert "Bearer deepseek-secret-key" not in rendered


def test_suppresses_full_message_prompt_text_and_content_fields() -> None:
    full_message = "Пользователь подробно описывает личную историю и ответы интервью."
    full_prompt = [{"role": "user", "content": full_message}]

    context = redact_context(
        {
            "message": full_message,
            "prompt": full_prompt,
            "text": full_message,
            "content": full_message,
            "safe_count": 3,
        }
    )

    rendered = f"{context}"

    assert context["message"] == CONTENT_REDACTED
    assert context["prompt"] == CONTENT_REDACTED
    assert context["text"] == CONTENT_REDACTED
    assert context["content"] == CONTENT_REDACTED
    assert context["safe_count"] == 3
    assert full_message not in rendered


def test_structured_logger_attaches_redacted_context_to_record(
    caplog: LogCaptureFixture,
) -> None:
    logger = logging.getLogger("tg_typist.tests.structured")

    logger.propagate = True
    logger.setLevel(logging.INFO)

    with caplog.at_level(logging.INFO, logger="tg_typist.tests.structured"):
        get_logger("tg_typist.tests.structured").info(
            "deepseek_request_failed",
            telegram_bot_token="telegram-token-secret",
            deepseek_api_key="deepseek-api-key-secret",
            database_url="postgresql+asyncpg://user:db_password@localhost:5432/db",
            authorization="Bearer deepseek-api-key-secret",
            message="full user message must not be logged",
            prompt={"messages": ["full prompt must not be logged"]},
            request_message_count=5,
        )

    record = caplog.records[0]
    structured = cast(dict[str, Any], record.__dict__["structured"])
    rendered = caplog.text

    assert structured["telegram_bot_token"] == REDACTED
    assert structured["deepseek_api_key"] == REDACTED
    assert structured["database_url"] == "postgresql+asyncpg://user:***@localhost:5432/db"
    assert structured["authorization"] == REDACTED
    assert structured["message"] == CONTENT_REDACTED
    assert structured["prompt"] == CONTENT_REDACTED
    assert structured["request_message_count"] == 5
    assert "telegram-token-secret" not in rendered
    assert "deepseek-api-key-secret" not in rendered
    assert "db_password" not in rendered
    assert "full user message must not be logged" not in rendered
    assert "full prompt must not be logged" not in rendered


def test_structured_formatter_outputs_json_without_secrets_or_full_text() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("tg_typist.tests.formatter")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.INFO)

    get_logger("tg_typist.tests.formatter").info(
        "telegram_update_received",
        telegram_user_id=123,
        telegram_bot_token="telegram-token-secret",
        deepseek_api_key="deepseek-api-key-secret",
        database_url="postgresql+asyncpg://user:db_password@localhost:5432/db",
        headers={"Authorization": "Bearer deepseek-api-key-secret"},
        text="full user text must not be logged",
        content="full prompt content must not be logged",
    )

    rendered = stream.getvalue()
    payload = json.loads(rendered)

    assert payload["event"] == "telegram_update_received"
    assert payload["telegram_user_id"] == 123
    assert payload["telegram_bot_token"] == REDACTED
    assert payload["deepseek_api_key"] == REDACTED
    assert payload["database_url"] == "postgresql+asyncpg://user:***@localhost:5432/db"
    assert payload["headers"] == {"Authorization": REDACTED}
    assert payload["text"] == CONTENT_REDACTED
    assert payload["content"] == CONTENT_REDACTED
    assert "telegram-token-secret" not in rendered
    assert "deepseek-api-key-secret" not in rendered
    assert "db_password" not in rendered
    assert "full user text must not be logged" not in rendered
    assert "full prompt content must not be logged" not in rendered
