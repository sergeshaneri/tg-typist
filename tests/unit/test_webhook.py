"""Telegram webhook secret verification tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from fastapi.testclient import TestClient
from httpx import Response

from tg_typist.main import create_app
from tg_typist.settings import load_settings

_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
_PRODUCTION_SECRET = "test-webhook-secret-value"


def _production_client() -> TestClient:
    settings = load_settings(
        {
            "ENVIRONMENT": "production",
            "TELEGRAM_BOT_TOKEN": "123456:test-token",
            "TELEGRAM_WEBHOOK_SECRET": _PRODUCTION_SECRET,
            "PUBLIC_WEBHOOK_BASE_URL": "https://example.invalid",
            "DEEPSEEK_API_KEY": "test-deepseek-key",
            "DEEPSEEK_MODEL": "test-model",
            "DATABASE_URL": "postgresql://user:password@example.invalid:5432/app",
        }
    )
    return TestClient(create_app(settings))


def _post_webhook(client: TestClient, headers: Mapping[str, str] | None = None) -> Response:
    return cast(
        Response,
        client.post("/telegram/webhook", json={"update_id": 12345}, headers=headers),
    )


def test_production_webhook_accepts_correct_secret_header() -> None:
    client = _production_client()

    response = _post_webhook(client, {_SECRET_HEADER: _PRODUCTION_SECRET})

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


def test_production_webhook_rejects_missing_secret_header() -> None:
    client = _production_client()

    response = _post_webhook(client)

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_production_webhook_rejects_wrong_secret_without_leaking_secret() -> None:
    client = _production_client()

    response = _post_webhook(client, {_SECRET_HEADER: "wrong-secret"})

    assert response.status_code == 403
    assert _PRODUCTION_SECRET not in response.text


def test_test_environment_webhook_accepts_without_secret_header() -> None:
    settings = load_settings({"ENVIRONMENT": "test"})
    client = TestClient(create_app(settings))

    response = _post_webhook(client)

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
