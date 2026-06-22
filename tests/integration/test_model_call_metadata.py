"""Integration tests for model-call metadata persistence."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from tg_typist.db.base import Base
from tg_typist.db.models import (
    FALLBACK_POLICY_NONE,
    FALLBACK_POLICY_TAIL_WINDOW,
    FALLBACK_REASON_CONTEXT_LIMIT,
    HISTORY_POLICY_FULL_ACTIVE_SESSION,
    HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT,
    MODEL_CALL_STATUS_CONTEXT_LIMIT,
    MODEL_CALL_STATUS_SUCCESS,
)
from tg_typist.db.repositories import (
    InterviewSessionRepository,
    MessageRepository,
    ProcessedTelegramUpdateRepository,
    TelegramUserRepository,
)
from tg_typist.llm.deepseek import DeepSeekFailure, DeepSeekSuccess
from tg_typist.llm.errors import DEEPSEEK_ERROR_CONTEXT_LIMIT, DeepSeekError
from tg_typist.llm.history import LLMMessage, PromptHistory
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


async def create_user_message(db_session: AsyncSession) -> tuple[UUID, UUID]:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=9101,
        telegram_chat_id=9201,
    )
    active_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )
    await ProcessedTelegramUpdateRepository(db_session).record_received(update_id=9301)
    user_message = await MessageRepository(db_session).save_user_message(
        session_id=active_session.id,
        text="raw user text must stay out of model-call metadata",
        telegram_update_id=9301,
        telegram_message_id=9401,
    )
    return active_session.id, user_message.id


def full_history() -> PromptHistory:
    messages = (
        LLMMessage(role="system", content="system rules"),
        LLMMessage(role="user", content="raw user text must stay out"),
    )
    return PromptHistory(
        system_prompt_version="test-prompt-v1",
        history_policy=HISTORY_POLICY_FULL_ACTIVE_SESSION,
        fallback_policy=FALLBACK_POLICY_NONE,
        fallback_reason=None,
        messages=messages,
        request_message_count=len(messages),
        request_char_count=sum(len(message.content) for message in messages),
    )


async def test_successful_deepseek_result_updates_model_call_metadata(
    db_session: AsyncSession,
) -> None:
    session_id, user_message_id = await create_user_message(db_session)
    result = DeepSeekSuccess(
        text="assistant answer is not stored in model-call metadata",
        model="deepseek-v4-flash",
        finish_reason="stop",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        latency_ms=123,
    )

    service = InterviewService(db_session)
    pending_call = await service.create_pending_model_call(
        session_id=session_id,
        user_message_id=user_message_id,
        model="deepseek-v4-flash",
        history=full_history(),
    )
    assert pending_call.status == "pending"

    model_call = await service.update_model_call_metadata(
        model_call_id=pending_call.id,
        result=result,
        history=full_history(),
    )

    assert model_call.status == MODEL_CALL_STATUS_SUCCESS
    assert model_call.model == "deepseek-v4-flash"
    assert model_call.system_prompt_version == "test-prompt-v1"
    assert model_call.history_policy == HISTORY_POLICY_FULL_ACTIVE_SESSION
    assert model_call.fallback_policy == FALLBACK_POLICY_NONE
    assert model_call.fallback_reason is None
    assert model_call.request_message_count == 2
    assert model_call.request_char_count == full_history().request_char_count
    assert model_call.latency_ms == 123
    assert model_call.prompt_tokens == 10
    assert model_call.completion_tokens == 5
    assert model_call.total_tokens == 15
    assert model_call.error_code is None
    assert model_call.error_message_redacted is None


async def test_context_limit_failure_persists_fallback_metadata_without_raw_prompt(
    db_session: AsyncSession,
) -> None:
    session_id, user_message_id = await create_user_message(db_session)
    fallback_history = PromptHistory(
        system_prompt_version="test-prompt-v1",
        history_policy=HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT,
        fallback_policy=FALLBACK_POLICY_TAIL_WINDOW,
        fallback_reason=FALLBACK_REASON_CONTEXT_LIMIT,
        messages=(
            LLMMessage(role="system", content="system rules"),
            LLMMessage(role="user", content="latest tail text"),
        ),
        request_message_count=2,
        request_char_count=len("system rules" + "latest tail text"),
    )
    result = DeepSeekFailure(
        error=DeepSeekError(
            code=DEEPSEEK_ERROR_CONTEXT_LIMIT,
            message_redacted="context length exceeded",
            status_code=422,
        ),
        latency_ms=456,
        used_context_fallback=True,
    )

    model_call = await InterviewService(db_session).record_model_call_metadata(
        session_id=session_id,
        user_message_id=user_message_id,
        model="deepseek-v4-flash",
        history=fallback_history,
        result=result,
    )

    assert model_call.status == MODEL_CALL_STATUS_CONTEXT_LIMIT
    assert model_call.history_policy == HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT
    assert model_call.fallback_policy == FALLBACK_POLICY_TAIL_WINDOW
    assert model_call.fallback_reason == FALLBACK_REASON_CONTEXT_LIMIT
    assert model_call.request_message_count == 2
    assert model_call.request_char_count == fallback_history.request_char_count
    assert model_call.latency_ms == 456
    assert model_call.error_code == DEEPSEEK_ERROR_CONTEXT_LIMIT
    assert model_call.error_message_redacted == "context length exceeded"
    assert "raw user text" not in (model_call.error_message_redacted or "")
    assert "latest tail text" not in (model_call.error_message_redacted or "")
