"""Integration tests for local repository operations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from tg_typist.db.base import Base
from tg_typist.db.models import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    MODEL_CALL_STATUS_PENDING,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_CLOSED,
    InterviewSession,
    Message,
    ModelCall,
    ProcessedTelegramUpdate,
    TelegramUser,
)
from tg_typist.db.repositories import (
    UPDATE_STATUS_PROCESSED,
    UPDATE_STATUS_RECEIVED,
    InterviewSessionRepository,
    MessageRepository,
    ModelCallRepository,
    ProcessedTelegramUpdateRepository,
    TelegramUserRepository,
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


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session


async def count_rows(session: AsyncSession, model: type[object]) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar_one()


async def test_user_upsert_creates_then_updates_minimal_profile(db_session: AsyncSession) -> None:
    users = TelegramUserRepository(db_session)
    first_seen_at = datetime(2026, 1, 1, tzinfo=UTC)
    second_seen_at = datetime(2026, 1, 2, tzinfo=UTC)

    created = await users.upsert(
        telegram_user_id=1001,
        telegram_chat_id=2001,
        username="first",
        first_name="Test",
        language_code="ru",
        last_seen_at=first_seen_at,
    )
    updated = await users.upsert(
        telegram_user_id=1001,
        telegram_chat_id=2002,
        username="second",
        first_name=None,
        language_code="en",
        last_seen_at=second_seen_at,
    )

    assert updated.id == created.id
    assert updated.telegram_chat_id == 2002
    assert updated.username == "second"
    assert updated.first_name is None
    assert updated.language_code == "en"
    assert updated.last_seen_at == second_seen_at
    assert await count_rows(db_session, TelegramUser) == 1


async def test_get_or_create_active_session_reuses_one_active_session(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=1002,
        telegram_chat_id=2002,
    )
    sessions = InterviewSessionRepository(db_session)

    created = await sessions.get_or_create_active(
        user_id=user.id,
        system_prompt_version="v1",
    )
    reused = await sessions.get_or_create_active(
        user_id=user.id,
        system_prompt_version="v2",
    )

    assert reused.id == created.id
    assert reused.status == SESSION_STATUS_ACTIVE
    assert reused.system_prompt_version == "v1"
    assert await count_rows(db_session, InterviewSession) == 1


async def test_processed_update_and_user_message_are_idempotent(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=1003,
        telegram_chat_id=2003,
    )
    interview_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )
    updates = ProcessedTelegramUpdateRepository(db_session)
    messages = MessageRepository(db_session)

    accepted = await updates.record_received(
        update_id=3003,
        telegram_user_id=1003,
        telegram_chat_id=2003,
        telegram_message_id=4003,
    )
    duplicate = await updates.record_received(
        update_id=3003,
        telegram_user_id=9999,
        telegram_chat_id=9999,
        telegram_message_id=9999,
    )
    first_message = await messages.save_user_message(
        session_id=interview_session.id,
        text="harmless repository test user text",
        telegram_update_id=3003,
        telegram_message_id=4003,
    )
    replay_message = await messages.save_user_message(
        session_id=interview_session.id,
        text="different duplicate text must not overwrite",
        telegram_update_id=3003,
        telegram_message_id=4999,
    )

    assert accepted.created is True
    assert duplicate.created is False
    assert duplicate.update.update_id == accepted.update.update_id
    assert duplicate.update.telegram_user_id == 1003
    assert duplicate.update.status == UPDATE_STATUS_RECEIVED
    assert replay_message.id == first_message.id
    assert replay_message.text == "harmless repository test user text"
    assert await count_rows(db_session, ProcessedTelegramUpdate) == 1
    assert await count_rows(db_session, Message) == 1


async def test_model_call_metadata_update_and_assistant_message_link(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=1004,
        telegram_chat_id=2004,
    )
    interview_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
        system_prompt_version="prompt-2026-06-21",
    )
    await ProcessedTelegramUpdateRepository(db_session).record_received(update_id=3004)
    messages = MessageRepository(db_session)
    user_message = await messages.save_user_message(
        session_id=interview_session.id,
        text="short local fixture text",
        telegram_update_id=3004,
        telegram_message_id=4004,
    )
    model_calls = ModelCallRepository(db_session)

    model_call = await model_calls.create_pending(
        session_id=interview_session.id,
        user_message_id=user_message.id,
        model="deepseek-chat-test",
        system_prompt_version="prompt-2026-06-21",
        request_message_count=2,
        request_char_count=48,
    )
    assert model_call.status == MODEL_CALL_STATUS_PENDING

    updated_call = await model_calls.update_result(
        model_call.id,
        status="success",
        latency_ms=123,
        prompt_tokens=10,
        completion_tokens=11,
        total_tokens=21,
    )
    assistant_message = await messages.save_assistant_message(
        session_id=interview_session.id,
        text="assistant fixture response",
        model_call_id=model_call.id,
        telegram_message_id=5004,
    )
    await ProcessedTelegramUpdateRepository(db_session).mark_processed(3004)
    ordered_messages = await messages.list_for_session(interview_session.id)

    assert updated_call.status == "success"
    assert updated_call.latency_ms == 123
    assert updated_call.total_tokens == 21
    assert assistant_message.role == MESSAGE_ROLE_ASSISTANT
    assert assistant_message.model_call_id == model_call.id
    assert [message.role for message in ordered_messages] == [
        MESSAGE_ROLE_USER,
        MESSAGE_ROLE_ASSISTANT,
    ]
    assert ordered_messages[0].id == user_message.id
    assert ordered_messages[1].id == assistant_message.id
    processed_update = await ProcessedTelegramUpdateRepository(db_session).get(3004)
    assert processed_update is not None
    assert processed_update.status == UPDATE_STATUS_PROCESSED
    assert processed_update.processed_at is not None
    assert await count_rows(db_session, ModelCall) == 1


async def test_reset_archives_old_session_and_active_history_starts_empty(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=1005,
        telegram_chat_id=2005,
    )
    sessions = InterviewSessionRepository(db_session)
    messages = MessageRepository(db_session)
    old_session = await sessions.get_or_create_active(user_id=user.id)
    await ProcessedTelegramUpdateRepository(db_session).record_received(update_id=3005)
    old_user_message = await messages.save_user_message(
        session_id=old_session.id,
        text="old active user message",
        telegram_update_id=3005,
        telegram_message_id=4005,
    )
    old_assistant_message = await messages.save_assistant_message(
        session_id=old_session.id,
        text="old active assistant response",
        telegram_message_id=5005,
    )
    old_user_message.created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    old_assistant_message.created_at = datetime(2026, 1, 1, 12, 1, tzinfo=UTC)
    await db_session.flush()

    before_reset_history = await messages.list_active_session_history_for_user(user.id)
    new_session = await sessions.reset_active_for_user(
        user_id=user.id,
        reset_reason="user /reset command",
    )
    after_reset_history = await messages.list_active_session_history_for_user(user.id)
    await ProcessedTelegramUpdateRepository(db_session).record_received(update_id=3006)
    new_message = await messages.save_user_message(
        session_id=new_session.id,
        text="new active user message",
        telegram_update_id=3006,
        telegram_message_id=4006,
    )
    new_history = await messages.list_active_session_history_for_user(user.id)

    assert [message.id for message in before_reset_history] == [
        old_user_message.id,
        old_assistant_message.id,
    ]
    assert new_session.id != old_session.id
    assert new_session.status == SESSION_STATUS_ACTIVE
    assert old_session.status == SESSION_STATUS_CLOSED
    assert old_session.closed_at is not None
    assert old_session.reset_reason == "user /reset command"
    assert after_reset_history == []
    assert [message.id for message in new_history] == [new_message.id]
    assert await messages.list_for_session(old_session.id) == [
        old_user_message,
        old_assistant_message,
    ]
    assert await count_rows(db_session, InterviewSession) == 2
    assert await count_rows(db_session, Message) == 3


async def test_reset_without_existing_active_session_creates_new_active_session(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=1006,
        telegram_chat_id=2006,
    )
    sessions = InterviewSessionRepository(db_session)

    new_session = await sessions.reset_active_for_user(
        user_id=user.id,
        reset_reason="first reset command",
    )

    assert new_session.status == SESSION_STATUS_ACTIVE
    assert new_session.closed_at is None
    assert new_session.reset_reason is None
    assert await sessions.get_active_for_user(user.id) == new_session
    assert await MessageRepository(db_session).list_active_session_history_for_user(user.id) == []
    assert await count_rows(db_session, InterviewSession) == 1
