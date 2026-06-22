from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

settings_module = importlib.import_module("tg_typist.settings")
SettingsError = settings_module.SettingsError
load_settings = settings_module.load_settings


def test_production_requires_live_secrets() -> None:
    with pytest.raises(SettingsError, match="TELEGRAM_BOT_TOKEN"):
        load_settings({"ENVIRONMENT": "production"})


def test_production_loads_required_environment() -> None:
    settings = load_settings(
        {
            "ENVIRONMENT": "production",
            "TELEGRAM_BOT_TOKEN": "123456:telegram-token",
            "TELEGRAM_WEBHOOK_SECRET": "webhook-secret",
            "PUBLIC_WEBHOOK_BASE_URL": "https://bot.example.com",
            "DEEPSEEK_API_KEY": "deepseek-api-key",
            "DEEPSEEK_MODEL": "deepseek-current-model",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/tg_typist",
            "PORT": "12345",
        }
    )

    assert settings.environment == "production"
    assert settings.telegram_bot_token == "123456:telegram-token"
    assert settings.deepseek_model == "deepseek-current-model"
    assert settings.port == 12345


def test_test_environment_has_safe_defaults_without_live_secrets() -> None:
    settings = load_settings({"ENVIRONMENT": "test"})

    assert settings.environment == "test"
    assert settings.telegram_bot_token is None
    assert settings.telegram_webhook_secret is None
    assert settings.deepseek_api_key is None
    assert settings.database_url is None
    assert settings.deepseek_model == "test-model"
    assert settings.port == 8000
    assert settings.admin_telegram_ids == ()


def test_railway_port_is_parsed_from_environment() -> None:
    settings = load_settings({"ENVIRONMENT": "test", "PORT": "43210"})

    assert settings.port == 43210


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PORT", "0"),
        ("PORT", "65536"),
        ("MAX_MESSAGE_CHARS", "0"),
        ("RATE_LIMIT_MESSAGES", "-1"),
        ("RATE_LIMIT_WINDOW_SECONDS", "0"),
        ("DEEPSEEK_TIMEOUT_SECONDS", "0"),
        ("DEEPSEEK_MAX_RETRIES", "-1"),
    ],
)
def test_invalid_numeric_limits_are_rejected(name: str, value: str) -> None:
    with pytest.raises(SettingsError, match=name):
        load_settings({"ENVIRONMENT": "test", name: value})


def test_admin_ids_are_parsed_as_integers() -> None:
    settings = load_settings({"ENVIRONMENT": "test", "ADMIN_TELEGRAM_IDS": "1, 2;3"})

    assert settings.admin_telegram_ids == (1, 2, 3)


def test_safe_output_and_repr_redact_secrets() -> None:
    settings = load_settings(
        {
            "ENVIRONMENT": "production",
            "TELEGRAM_BOT_TOKEN": "telegram-token-secret",
            "TELEGRAM_WEBHOOK_SECRET": "webhook-secret-value",
            "PUBLIC_WEBHOOK_BASE_URL": "https://bot.example.com",
            "DEEPSEEK_API_KEY": "deepseek-api-key-secret",
            "DEEPSEEK_MODEL": "deepseek-current-model",
            "DATABASE_URL": "postgresql+asyncpg://db_user:db_password@db.example.com:5432/db",
        }
    )

    safe_text = f"{settings.safe_dict()} {settings!r}"

    assert "telegram-token-secret" not in safe_text
    assert "webhook-secret-value" not in safe_text
    assert "deepseek-api-key-secret" not in safe_text
    assert "db_password" not in safe_text
    assert "db_user:***@db.example.com:5432/db" in safe_text
