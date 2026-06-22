"""Interview service skeletons without live LLM dependencies."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tg_typist.bot.messages import TEXT_PLACEHOLDER_MESSAGE
from tg_typist.db.repositories import (
    InterviewSessionRepository,
    MessageRepository,
    ProcessedTelegramUpdateRepository,
    TelegramUserRepository,
)


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
