"""Integration tests for active-session prompt history building."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from tg_typist.db.base import Base
from tg_typist.db.repositories import (
    InterviewSessionRepository,
    MessageRepository,
    ProcessedTelegramUpdateRepository,
    TelegramUserRepository,
)
from tg_typist.llm.history import (
    FALLBACK_POLICY_NONE,
    FALLBACK_POLICY_TAIL_WINDOW,
    FALLBACK_REASON_CONTEXT_LIMIT,
    HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT,
    HistoryBuilder,
)
from tg_typist.llm.prompts import SystemPrompt


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


def load_test_prompt() -> SystemPrompt:
    return SystemPrompt(version="test-system-v1", text="system rules")


async def test_history_for_user_without_active_messages_contains_only_system_prompt(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=8101,
        telegram_chat_id=9101,
    )

    history = await HistoryBuilder(
        db_session,
        system_prompt_loader=load_test_prompt,
    ).build_for_user(user.id)

    assert history.system_prompt_version == "test-system-v1"
    assert history.fallback_policy == FALLBACK_POLICY_NONE
    assert history.fallback_reason is None
    assert [(message.role, message.content) for message in history.messages] == [
        ("system", "system rules"),
    ]
    assert history.request_message_count == 1
    assert history.request_char_count == len("system rules")


async def test_history_includes_full_active_session_and_excludes_archived_session(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=8102,
        telegram_chat_id=9102,
    )
    sessions = InterviewSessionRepository(db_session)
    messages = MessageRepository(db_session)
    updates = ProcessedTelegramUpdateRepository(db_session)
    old_session = await sessions.get_or_create_active(user_id=user.id)
    await updates.record_received(update_id=8201)
    await messages.save_user_message(
        session_id=old_session.id,
        text="archived user text",
        telegram_update_id=8201,
        telegram_message_id=8301,
    )
    await messages.save_assistant_message(
        session_id=old_session.id,
        text="archived assistant text",
    )

    active_session = await sessions.reset_active_for_user(
        user_id=user.id,
        reset_reason="history builder test reset",
    )
    await updates.record_received(update_id=8202)
    await messages.save_user_message(
        session_id=active_session.id,
        text="active user text",
        telegram_update_id=8202,
        telegram_message_id=8302,
    )
    await messages.save_assistant_message(
        session_id=active_session.id,
        text="active assistant text",
    )

    history = await HistoryBuilder(
        db_session,
        system_prompt_loader=load_test_prompt,
    ).build_for_user(user.id)

    assert [(message.role, message.content) for message in history.messages] == [
        ("system", "system rules"),
        ("user", "active user text"),
        ("assistant", "active assistant text"),
    ]
    assert history.request_message_count == 3
    assert history.request_char_count == len(
        "system rules" + "active user text" + "active assistant text"
    )
    assert history.fallback_policy == FALLBACK_POLICY_NONE
    assert history.fallback_reason is None


async def test_history_includes_latest_saved_user_message(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=8103,
        telegram_chat_id=9103,
    )
    active_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )
    updates = ProcessedTelegramUpdateRepository(db_session)
    messages = MessageRepository(db_session)
    await updates.record_received(update_id=8203)
    await messages.save_user_message(
        session_id=active_session.id,
        text="earlier active user text",
        telegram_update_id=8203,
        telegram_message_id=8303,
    )
    await updates.record_received(update_id=8204)
    await messages.save_user_message(
        session_id=active_session.id,
        text="latest active user text",
        telegram_update_id=8204,
        telegram_message_id=8304,
    )

    history = await HistoryBuilder(
        db_session,
        system_prompt_loader=load_test_prompt,
    ).build_for_user(user.id)

    assert [(message.role, message.content) for message in history.messages] == [
        ("system", "system rules"),
        ("user", "earlier active user text"),
        ("user", "latest active user text"),
    ]


async def test_history_excludes_failed_assistant_messages(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=8104,
        telegram_chat_id=9104,
    )
    active_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )
    await MessageRepository(db_session).save_assistant_message(
        session_id=active_session.id,
        text="failed assistant text",
        status="failed_to_send",
    )

    history = await HistoryBuilder(
        db_session,
        system_prompt_loader=load_test_prompt,
    ).build_for_user(user.id)

    assert [(message.role, message.content) for message in history.messages] == [
        ("system", "system rules"),
    ]


async def test_tail_window_fallback_keeps_latest_messages_without_summary(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=8105,
        telegram_chat_id=9105,
    )
    active_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )
    messages = MessageRepository(db_session)
    updates = ProcessedTelegramUpdateRepository(db_session)
    for update_id, text in (
        (8205, "old message"),
        (8206, "middle message"),
        (8207, "latest message"),
    ):
        await updates.record_received(update_id=update_id)
        await messages.save_user_message(
            session_id=active_session.id,
            text=text,
            telegram_update_id=update_id,
            telegram_message_id=update_id + 100,
        )

    history = await HistoryBuilder(
        db_session,
        system_prompt_loader=load_test_prompt,
    ).build_tail_window_for_user(
        user.id,
        max_prompt_chars=len("system rules" + "middle message" + "latest message"),
    )

    assert history.history_policy == HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT
    assert history.fallback_policy == FALLBACK_POLICY_TAIL_WINDOW
    assert history.fallback_reason == FALLBACK_REASON_CONTEXT_LIMIT
    assert [(message.role, message.content) for message in history.messages] == [
        ("system", "system rules"),
        ("user", "middle message"),
        ("user", "latest message"),
    ]
    assert "summary" not in " ".join(message.content for message in history.messages).lower()
    assert history.request_message_count == 3
    assert history.request_char_count == len(
        "system rules" + "middle message" + "latest message"
    )
