"""Telegram webhook secret verification tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from tg_typist.db.base import Base
from tg_typist.db.models import ProcessedTelegramUpdate
from tg_typist.db.repositories import UPDATE_STATUS_PROCESSED
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
    app = create_app(settings)
    app.state.session_factory = None
    return TestClient(app)


def _post_webhook(client: TestClient, headers: Mapping[str, str] | None = None) -> Response:
    return cast(
        Response,
        client.post("/telegram/webhook", json={"update_id": 12345}, headers=headers),
    )


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _count_processed_updates(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(ProcessedTelegramUpdate))
    return result.scalar_one()


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


async def test_webhook_records_update_id_before_dispatch_and_skips_duplicate(
    engine: AsyncEngine,
) -> None:
    settings = load_settings({"ENVIRONMENT": "test"})
    app = create_app(settings)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    update = {
        "update_id": 12345,
        "message": {
            "message_id": 678,
            "from": {"id": 111},
            "chat": {"id": 222},
            "text": "safe fixture text",
        },
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        first_response = await client.post("/telegram/webhook", json=update)
        duplicate_response = await client.post("/telegram/webhook", json=update)

    async with session_factory() as session:
        stored_update = await session.get(ProcessedTelegramUpdate, 12345)
        update_count = await _count_processed_updates(session)

    assert first_response.status_code == 202
    assert first_response.json() == {"status": "accepted"}
    assert duplicate_response.status_code == 202
    assert duplicate_response.json() == {"status": "duplicate"}
    assert stored_update is not None
    assert stored_update.status == UPDATE_STATUS_PROCESSED
    assert stored_update.telegram_user_id == 111
    assert stored_update.telegram_chat_id == 222
    assert stored_update.telegram_message_id == 678
    assert update_count == 1
