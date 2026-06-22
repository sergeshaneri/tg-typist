"""Build DeepSeek prompt history from the active interview session."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tg_typist.db.models import HISTORY_POLICY_FULL_ACTIVE_SESSION
from tg_typist.db.repositories import MessageRepository
from tg_typist.llm.prompts import SystemPrompt, load_system_prompt

LLMRole = Literal["system", "user", "assistant"]
HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT = "tail_window_after_context_limit"
FALLBACK_POLICY_NONE = "none"
FALLBACK_POLICY_TAIL_WINDOW = "tail_window"
FALLBACK_REASON_CONTEXT_LIMIT = "context_limit"


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """One message ready for provider prompt assembly."""

    role: LLMRole
    content: str


@dataclass(frozen=True, slots=True)
class PromptHistory:
    """Full active-session prompt payload and metadata."""

    system_prompt_version: str
    history_policy: str
    fallback_policy: str
    fallback_reason: str | None
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
            history_policy=HISTORY_POLICY_FULL_ACTIVE_SESSION,
            fallback_policy=FALLBACK_POLICY_NONE,
            fallback_reason=None,
            messages=messages,
            request_message_count=len(messages),
            request_char_count=sum(len(message.content) for message in messages),
        )

    async def build_tail_window_for_user(
        self,
        user_id: UUID,
        *,
        max_prompt_chars: int,
    ) -> PromptHistory:
        """Return system prompt plus latest active messages under a character budget.

        This is an explicit context-limit fallback. It keeps raw recent messages and
        does not summarize or synthesize conversation state.
        """

        if max_prompt_chars < 1:
            raise ValueError("max_prompt_chars must be greater than zero")

        system_prompt = self._system_prompt_loader()
        stored_messages = await MessageRepository(
            self._session
        ).list_active_session_history_for_user(user_id)
        selected_messages: list[LLMMessage] = []
        used_chars = len(system_prompt.text)
        for message in reversed(stored_messages):
            if message.role not in ("user", "assistant"):
                continue
            llm_message = LLMMessage(role=cast(LLMRole, message.role), content=message.text)
            next_used_chars = used_chars + len(llm_message.content)
            if selected_messages and next_used_chars > max_prompt_chars:
                break
            if not selected_messages or next_used_chars <= max_prompt_chars:
                selected_messages.append(llm_message)
                used_chars = next_used_chars

        messages = (
            LLMMessage(role="system", content=system_prompt.text),
            *reversed(selected_messages),
        )
        return PromptHistory(
            system_prompt_version=system_prompt.version,
            history_policy=HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT,
            fallback_policy=FALLBACK_POLICY_TAIL_WINDOW,
            fallback_reason=FALLBACK_REASON_CONTEXT_LIMIT,
            messages=messages,
            request_message_count=len(messages),
            request_char_count=sum(len(message.content) for message in messages),
        )
