"""FastAPI app factory and webhook shell tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tg_typist.main import create_app
from tg_typist.settings import load_settings


def test_health_works_without_live_credentials() -> None:
    settings = load_settings({"ENVIRONMENT": "test"})
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "tg-typist",
        "version": "0.1.0",
        "environment": "test",
    }


def test_health_response_does_not_expose_secret_settings() -> None:
    settings = load_settings(
        {
            "ENVIRONMENT": "test",
            "TELEGRAM_BOT_TOKEN": "123456:secret-token",
            "TELEGRAM_WEBHOOK_SECRET": "secret-webhook-value",
            "DEEPSEEK_API_KEY": "deepseek-secret-value",
            "DATABASE_URL": "postgresql://user:secret-db-password@example.invalid:5432/app"
        }
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")

    body = response.text
    assert response.status_code == 200
    assert "123456:secret-token" not in body
    assert "secret-webhook-value" not in body
    assert "deepseek-secret-value" not in body
    assert "secret-db-password" not in body
    assert "database" not in body.lower()
    assert set(response.json()) == {"status", "service", "version", "environment"}


def test_telegram_webhook_shell_accepts_minimal_update_without_external_calls() -> None:
    settings = load_settings({"ENVIRONMENT": "test"})
    client = TestClient(create_app(settings))

    response = client.post("/telegram/webhook", json={"update_id": 12345})

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
