"""Build DeepSeek prompt history from the active interview session."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tg_typist.db.repositories import MessageRepository
from tg_typist.llm.prompts import SystemPrompt, load_system_prompt

LLMRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """One message ready for provider prompt assembly."""

    role: LLMRole
    content: str


@dataclass(frozen=True, slots=True)
class PromptHistory:
    """Full active-session prompt payload and metadata."""

    system_prompt_version: str
    messages: tuple[LLMMessage, ...]
    request_message_count: int
    request_char_count: int


class HistoryBuilder:
    """Build prompt history without contacting the model provider."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        system_prompt_loader: Callable[[], SystemPrompt] = load_system_prompt,
    ) -> None:
        self._session = session
        self._system_prompt_loader = system_prompt_loader

    async def build_for_user(self, user_id: UUID) -> PromptHistory:
        """Return system prompt plus saved user/assistant active-session messages."""

        system_prompt = self._system_prompt_loader()
        stored_messages = await MessageRepository(
            self._session
        ).list_active_session_history_for_user(user_id)
        messages = (
            LLMMessage(role="system", content=system_prompt.text),
            *(
                LLMMessage(role=cast(LLMRole, message.role), content=message.text)
                for message in stored_messages
                if message.role in ("user", "assistant")
            ),
        )

        return PromptHistory(
            system_prompt_version=system_prompt.version,
            messages=messages,
            request_message_count=len(messages),
            request_char_count=sum(len(message.content) for message in messages),
        )
