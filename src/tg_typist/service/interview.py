"""Interview service skeletons without live LLM dependencies."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tg_typist.bot.messages import TEXT_PLACEHOLDER_MESSAGE
from tg_typist.db.models import (
    MODEL_CALL_STATUS_CONTEXT_LIMIT,
    MODEL_CALL_STATUS_PROVIDER_ERROR,
    MODEL_CALL_STATUS_RATE_LIMITED,
    MODEL_CALL_STATUS_SUCCESS,
    MODEL_CALL_STATUS_TIMEOUT,
    MODEL_CALL_STATUS_UNEXPECTED_ERROR,
    ModelCall,
)
from tg_typist.db.repositories import (
    InterviewSessionRepository,
    MessageRepository,
    ModelCallRepository,
    ProcessedTelegramUpdateRepository,
    TelegramUserRepository,
)
from tg_typist.llm.deepseek import DeepSeekFailure, DeepSeekResult, DeepSeekSuccess
from tg_typist.llm.errors import (
    DEEPSEEK_ERROR_CONTEXT_LIMIT,
    DEEPSEEK_ERROR_RATE_LIMIT,
    DEEPSEEK_ERROR_TIMEOUT,
)
from tg_typist.llm.history import PromptHistory


class InterviewService:
    """Persistence-backed interview service shell used before DeepSeek is wired in."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_text_message_shell(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
        text: str,
        telegram_update_id: int | None = None,
        telegram_message_id: int | None = None,
    ) -> str:
        """Persist inbound user text and return a deterministic no-DeepSeek placeholder."""

        user = await TelegramUserRepository(self._session).upsert(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
        )
        active_session = await InterviewSessionRepository(self._session).get_or_create_active(
            user_id=user.id,
        )

        updates = ProcessedTelegramUpdateRepository(self._session)
        if telegram_update_id is not None:
            await updates.record_received(
                update_id=telegram_update_id,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=telegram_message_id,
            )

        await MessageRepository(self._session).save_user_message(
            session_id=active_session.id,
            text=text,
            telegram_update_id=telegram_update_id,
            telegram_message_id=telegram_message_id,
        )

        if telegram_update_id is not None:
            await updates.mark_processed(telegram_update_id)

        return TEXT_PLACEHOLDER_MESSAGE

    async def record_model_call_metadata(
        self,
        *,
        session_id: UUID,
        user_message_id: UUID,
        model: str | None,
        history: PromptHistory,
        result: DeepSeekResult,
    ) -> ModelCall:
        """Persist model-call metadata without storing raw prompt or response payload."""

        model_call = await self.create_pending_model_call(
            session_id=session_id,
            user_message_id=user_message_id,
            model=model,
            history=history,
        )
        return await self.update_model_call_metadata(
            model_call_id=model_call.id,
            result=result,
            history=history,
        )

    async def create_pending_model_call(
        self,
        *,
        session_id: UUID,
        user_message_id: UUID,
        model: str | None,
        history: PromptHistory,
    ) -> ModelCall:
        """Create pending model-call metadata before issuing a provider request."""

        return await ModelCallRepository(self._session).create_pending(
            session_id=session_id,
            user_message_id=user_message_id,
            model=model,
            system_prompt_version=history.system_prompt_version,
            request_message_count=history.request_message_count,
            request_char_count=history.request_char_count,
            history_policy=history.history_policy,
            fallback_policy=history.fallback_policy,
            fallback_reason=history.fallback_reason,
        )

    async def update_model_call_metadata(
        self,
        *,
        model_call_id: UUID,
        result: DeepSeekResult,
        history: PromptHistory | None = None,
    ) -> ModelCall:
        """Finalize model-call metadata after provider success or failure."""

        model_calls = ModelCallRepository(self._session)

        if isinstance(result, DeepSeekSuccess):
            return await model_calls.update_result(
                model_call_id,
                status=MODEL_CALL_STATUS_SUCCESS,
                history_policy=history.history_policy if history is not None else None,
                fallback_policy=history.fallback_policy if history is not None else None,
                fallback_reason=history.fallback_reason if history is not None else None,
                request_message_count=(
                    history.request_message_count if history is not None else None
                ),
                request_char_count=history.request_char_count if history is not None else None,
                latency_ms=result.latency_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
            )

        return await model_calls.update_result(
            model_call_id,
            status=_status_for_failure(result),
            history_policy=history.history_policy if history is not None else None,
            fallback_policy=history.fallback_policy if history is not None else None,
            fallback_reason=history.fallback_reason if history is not None else None,
            request_message_count=history.request_message_count if history is not None else None,
            request_char_count=history.request_char_count if history is not None else None,
            latency_ms=result.latency_ms,
            error_code=result.error.code,
            error_message_redacted=result.error.message_redacted,
        )


def _status_for_failure(result: DeepSeekFailure) -> str:
    if result.error.code == DEEPSEEK_ERROR_TIMEOUT:
        return MODEL_CALL_STATUS_TIMEOUT
    if result.error.code == DEEPSEEK_ERROR_RATE_LIMIT:
        return MODEL_CALL_STATUS_RATE_LIMITED
    if result.error.code == DEEPSEEK_ERROR_CONTEXT_LIMIT:
        return MODEL_CALL_STATUS_CONTEXT_LIMIT
    if result.error.code:
        return MODEL_CALL_STATUS_PROVIDER_ERROR
    return MODEL_CALL_STATUS_UNEXPECTED_ERROR
