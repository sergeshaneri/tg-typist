"""Async repository operations for core interview persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_typist.db.models import (
    HISTORY_POLICY_FULL_ACTIVE_SESSION,
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    MESSAGE_STATUS_SAVED,
    MODEL_CALL_STATUS_PENDING,
    MODEL_PROVIDER_DEEPSEEK,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_CLOSED,
    InterviewSession,
    Message,
    ModelCall,
    ProcessedTelegramUpdate,
    TelegramUser,
    utc_now,
)

UPDATE_STATUS_FAILED = "failed"
UPDATE_STATUS_PROCESSED = "processed"
UPDATE_STATUS_RECEIVED = "received"


@dataclass(frozen=True)
class ProcessedUpdateRecordResult:
    """Result of accepting a Telegram update for idempotent processing."""

    update: ProcessedTelegramUpdate
    created: bool


class TelegramUserRepository:
    """Persistence operations for Telegram users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramUser | None:
        """Return a user by Telegram numeric ID, if known."""

        result = await self._session.execute(
            select(TelegramUser).where(TelegramUser.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str | None = None,
        last_seen_at: datetime | None = None,
    ) -> TelegramUser:
        """Create or update the minimal Telegram profile needed by the bot."""

        user = await self.get_by_telegram_user_id(telegram_user_id)
        seen_at = last_seen_at or utc_now()
        if user is None:
            user = TelegramUser(
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                username=username,
                first_name=first_name,
                language_code=language_code,
                last_seen_at=seen_at,
            )
            self._session.add(user)
        else:
            user.telegram_chat_id = telegram_chat_id
            user.username = username
            user.first_name = first_name
            user.language_code = language_code
            user.last_seen_at = seen_at
        await self._session.flush()
        return user


class InterviewSessionRepository:
    """Persistence operations for interview sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_for_user(self, user_id: UUID) -> InterviewSession | None:
        """Return the active session for a user, if one exists."""

        result = await self._session.execute(
            select(InterviewSession).where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == SESSION_STATUS_ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_active(
        self,
        *,
        user_id: UUID,
        system_prompt_version: str | None = None,
        history_policy: str = HISTORY_POLICY_FULL_ACTIVE_SESSION,
    ) -> InterviewSession:
        """Return the user's active session or create exactly one in this transaction."""

        active_session = await self.get_active_for_user(user_id)
        if active_session is not None:
            return active_session

        active_session = InterviewSession(
            user_id=user_id,
            system_prompt_version=system_prompt_version,
            history_policy=history_policy,
        )
        self._session.add(active_session)
        await self._session.flush()
        return active_session

    async def reset_active_for_user(
        self,
        *,
        user_id: UUID,
        reset_reason: str | None = None,
        system_prompt_version: str | None = None,
        history_policy: str = HISTORY_POLICY_FULL_ACTIVE_SESSION,
    ) -> InterviewSession:
        """Close the current active session, then create and return a new active one."""

        active_session = await self.get_active_for_user(user_id)
        if active_session is not None:
            active_session.status = SESSION_STATUS_CLOSED
            active_session.closed_at = utc_now()
            active_session.reset_reason = reset_reason
            await self._session.flush()

        new_session = InterviewSession(
            user_id=user_id,
            system_prompt_version=system_prompt_version,
            history_policy=history_policy,
        )
        self._session.add(new_session)
        await self._session.flush()
        return new_session


class ProcessedTelegramUpdateRepository:
    """Persistence operations for Telegram update idempotency records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, update_id: int) -> ProcessedTelegramUpdate | None:
        """Return a processed-update record by Telegram update ID."""

        return await self._session.get(ProcessedTelegramUpdate, update_id)

    async def record_received(
        self,
        *,
        update_id: int,
        telegram_user_id: int | None = None,
        telegram_chat_id: int | None = None,
        telegram_message_id: int | None = None,
    ) -> ProcessedUpdateRecordResult:
        """Insert a new update record or report that it was already accepted."""

        existing = await self.get(update_id)
        if existing is not None:
            return ProcessedUpdateRecordResult(update=existing, created=False)

        update = ProcessedTelegramUpdate(
            update_id=update_id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            status=UPDATE_STATUS_RECEIVED,
        )
        self._session.add(update)
        await self._session.flush()
        return ProcessedUpdateRecordResult(update=update, created=True)

    async def mark_processed(self, update_id: int, *, processed_at: datetime | None = None) -> None:
        """Mark an accepted Telegram update as processed."""

        update = await self.get(update_id)
        if update is None:
            raise ValueError(f"Unknown Telegram update_id: {update_id}")
        update.status = UPDATE_STATUS_PROCESSED
        update.processed_at = processed_at or utc_now()
        await self._session.flush()

    async def mark_failed(self, update_id: int) -> None:
        """Mark an accepted Telegram update as failed without deleting its idempotency record."""

        update = await self.get(update_id)
        if update is None:
            raise ValueError(f"Unknown Telegram update_id: {update_id}")
        update.status = UPDATE_STATUS_FAILED
        await self._session.flush()


class MessageRepository:
    """Persistence operations for user and assistant messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_message_by_update_id(self, telegram_update_id: int) -> Message | None:
        """Return the saved inbound message for a Telegram update, if any."""

        result = await self._session.execute(
            select(Message).where(
                Message.telegram_update_id == telegram_update_id,
                Message.role == MESSAGE_ROLE_USER,
            )
        )
        return result.scalar_one_or_none()

    async def save_user_message(
        self,
        *,
        session_id: UUID,
        text: str,
        telegram_update_id: int | None,
        telegram_message_id: int | None = None,
        source: str = "telegram",
    ) -> Message:
        """Save an inbound user message once for a Telegram update, when one is known."""

        if telegram_update_id is not None:
            existing = await self.get_user_message_by_update_id(telegram_update_id)
            if existing is not None:
                return existing

        message = Message(
            session_id=session_id,
            telegram_message_id=telegram_message_id,
            telegram_update_id=telegram_update_id,
            role=MESSAGE_ROLE_USER,
            text=text,
            source=source,
            status=MESSAGE_STATUS_SAVED,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def save_assistant_message(
        self,
        *,
        session_id: UUID,
        text: str,
        model_call_id: UUID | None = None,
        telegram_message_id: int | None = None,
        source: str = "deepseek",
        status: str = MESSAGE_STATUS_SAVED,
    ) -> Message:
        """Save an assistant response after a successful model result."""

        message = Message(
            session_id=session_id,
            telegram_message_id=telegram_message_id,
            role=MESSAGE_ROLE_ASSISTANT,
            text=text,
            source=source,
            model_call_id=model_call_id,
            status=status,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_for_session(self, session_id: UUID) -> list[Message]:
        """Return session messages in deterministic chronological order."""

        result = await self._session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(result.scalars().all())

    async def list_active_session_history_for_user(self, user_id: UUID) -> list[Message]:
        """Return saved user/assistant messages for the user's active session only."""

        result = await self._session.execute(
            select(Message)
            .join(InterviewSession, Message.session_id == InterviewSession.id)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == SESSION_STATUS_ACTIVE,
                Message.role.in_([MESSAGE_ROLE_USER, MESSAGE_ROLE_ASSISTANT]),
                Message.status == MESSAGE_STATUS_SAVED,
            )
            .order_by(Message.created_at, Message.id)
        )
        return list(result.scalars().all())


class ModelCallRepository:
    """Persistence operations for DeepSeek model-call metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self,
        *,
        session_id: UUID,
        user_message_id: UUID,
        model: str | None,
        system_prompt_version: str | None,
        request_message_count: int,
        request_char_count: int,
        provider: str = MODEL_PROVIDER_DEEPSEEK,
        history_policy: str = HISTORY_POLICY_FULL_ACTIVE_SESSION,
    ) -> ModelCall:
        """Create model-call metadata before issuing the provider request."""

        model_call = ModelCall(
            session_id=session_id,
            user_message_id=user_message_id,
            provider=provider,
            model=model,
            system_prompt_version=system_prompt_version,
            history_policy=history_policy,
            request_message_count=request_message_count,
            request_char_count=request_char_count,
            status=MODEL_CALL_STATUS_PENDING,
        )
        self._session.add(model_call)
        await self._session.flush()
        return model_call

    async def update_result(
        self,
        model_call_id: UUID,
        *,
        status: str,
        latency_ms: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        error_code: str | None = None,
        error_message_redacted: str | None = None,
    ) -> ModelCall:
        """Update metadata after a provider request succeeds or fails."""

        model_call = await self._session.get(ModelCall, model_call_id)
        if model_call is None:
            raise ValueError(f"Unknown model_call_id: {model_call_id}")

        model_call.status = status
        model_call.latency_ms = latency_ms
        model_call.prompt_tokens = prompt_tokens
        model_call.completion_tokens = completion_tokens
        model_call.total_tokens = total_tokens
        model_call.error_code = error_code
        model_call.error_message_redacted = error_message_redacted
        await self._session.flush()
        return model_call
