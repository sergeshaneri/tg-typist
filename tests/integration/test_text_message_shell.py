"""Integration tests for the text-message shell service."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from tg_typist.bot.messages import TEXT_PLACEHOLDER_MESSAGE
from tg_typist.db.base import Base
from tg_typist.db.models import MESSAGE_ROLE_USER, InterviewSession, Message, ModelCall
from tg_typist.db.repositories import UPDATE_STATUS_PROCESSED, ProcessedTelegramUpdateRepository
from tg_typist.service.interview import InterviewService


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


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session


async def count_rows(session: AsyncSession, model: type[object]) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar_one()


async def test_text_shell_saves_user_text_and_returns_placeholder_without_model_call(
    db_session: AsyncSession,
) -> None:
    service = InterviewService(db_session)

    response = await service.save_text_message_shell(
        telegram_user_id=1101,
        telegram_chat_id=2101,
        username="shell_test_user",
        first_name="Тест",
        language_code="ru",
        text="безопасный текст интеграционного теста",
        telegram_update_id=3101,
        telegram_message_id=4101,
    )

    messages = (await db_session.execute(select(Message))).scalars().all()
    processed_update = await ProcessedTelegramUpdateRepository(db_session).get(3101)
    assert response == TEXT_PLACEHOLDER_MESSAGE
    assert len(messages) == 1
    assert messages[0].role == MESSAGE_ROLE_USER
    assert messages[0].text == "безопасный текст интеграционного теста"
    assert messages[0].telegram_update_id == 3101
    assert messages[0].telegram_message_id == 4101
    assert processed_update is not None
    assert processed_update.status == UPDATE_STATUS_PROCESSED
    assert await count_rows(db_session, InterviewSession) == 1
    assert await count_rows(db_session, ModelCall) == 0


async def test_text_shell_reuses_active_session_for_same_telegram_user(
    db_session: AsyncSession,
) -> None:
    service = InterviewService(db_session)

    await service.save_text_message_shell(
        telegram_user_id=1102,
        telegram_chat_id=2102,
        username=None,
        first_name=None,
        language_code="ru",
        text="первое тестовое сообщение",
        telegram_update_id=3102,
        telegram_message_id=4102,
    )
    await service.save_text_message_shell(
        telegram_user_id=1102,
        telegram_chat_id=2102,
        username=None,
        first_name=None,
        language_code="ru",
        text="второе тестовое сообщение",
        telegram_update_id=3103,
        telegram_message_id=4103,
    )

    messages = (
        (
            await db_session.execute(select(Message).order_by(Message.created_at, Message.id))
        )
        .scalars()
        .all()
    )
    assert await count_rows(db_session, InterviewSession) == 1
    assert [message.session_id for message in messages] == [
        messages[0].session_id,
        messages[0].session_id,
    ]
    assert [message.text for message in messages] == [
        "первое тестовое сообщение",
        "второе тестовое сообщение",
    ]
    assert await count_rows(db_session, ModelCall) == 0
