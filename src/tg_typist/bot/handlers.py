"""Aiogram command and text handlers kept free of live network dependencies."""

from __future__ import annotations

from typing import Any, Protocol, TypedDict, cast

from tg_typist.bot.messages import (
    HELP_MESSAGE,
    PRIVACY_MESSAGE,
    RESET_MESSAGE,
    START_MESSAGE,
    TEXT_PLACEHOLDER_MESSAGE,
    UNSUPPORTED_MESSAGE,
)


class TelegramUserLike(Protocol):
    """Minimal Telegram user attributes needed for service hooks."""

    @property
    def id(self) -> int:
        """Telegram numeric user ID."""

    @property
    def username(self) -> str | None:
        """Telegram username, if present."""

    @property
    def first_name(self) -> str | None:
        """Telegram first name, if present."""

    @property
    def language_code(self) -> str | None:
        """Telegram language code, if present."""


class TelegramChatLike(Protocol):
    """Minimal Telegram chat attributes needed for service hooks."""

    @property
    def id(self) -> int:
        """Telegram numeric chat ID."""

    @property
    def type(self) -> str:
        """Telegram chat type, e.g. private/group/supergroup/channel."""


class AnswerableMessage(Protocol):
    """Small message protocol for deterministic handler tests without a Bot token."""

    @property
    def from_user(self) -> TelegramUserLike | None:
        """Sender, if Telegram provided one."""

    @property
    def chat(self) -> TelegramChatLike:
        """Chat where the command was received."""

    async def answer(self, text: str) -> Any:
        """Send a response to the chat."""


class TextMessage(AnswerableMessage, Protocol):
    """Small protocol for ordinary Telegram text messages."""

    @property
    def text(self) -> str | None:
        """Telegram text payload, if present."""

    @property
    def message_id(self) -> int:
        """Telegram message ID inside the chat."""


class CommandProfile(TypedDict):
    """Normalized Telegram identity fields for command persistence hooks."""

    telegram_user_id: int
    telegram_chat_id: int
    username: str | None
    first_name: str | None
    language_code: str | None


class CommandService(Protocol):
    """Optional persistence hook for later DB/webhook integration."""

    async def ensure_active_session(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
    ) -> None:
        """Create or resume an active interview session for `/start`."""

    async def reset_active_session(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
    ) -> None:
        """Reset the active interview session for `/reset`."""


class TextMessageService(Protocol):
    """Optional persistence hook for the no-DeepSeek text-message shell."""

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
        """Persist inbound text and return the placeholder response."""


async def handle_start(
    message: AnswerableMessage,
    command_service: CommandService | None = None,
) -> None:
    """Handle `/start` by optionally ensuring a session, then sending intro text."""

    if not _is_private_chat(message):
        return

    if command_service is not None:
        profile = _telegram_profile(message)
        if profile is not None:
            await command_service.ensure_active_session(
                telegram_user_id=profile["telegram_user_id"],
                telegram_chat_id=profile["telegram_chat_id"],
                username=profile["username"],
                first_name=profile["first_name"],
                language_code=profile["language_code"],
            )
    await message.answer(START_MESSAGE)


async def handle_help(message: AnswerableMessage) -> None:
    """Handle `/help`."""

    if not _is_private_chat(message):
        return

    await message.answer(HELP_MESSAGE)


async def handle_privacy(message: AnswerableMessage) -> None:
    """Handle `/privacy`."""

    if not _is_private_chat(message):
        return

    await message.answer(PRIVACY_MESSAGE)


async def handle_reset(
    message: AnswerableMessage,
    command_service: CommandService | None = None,
) -> None:
    """Handle `/reset` by optionally resetting a session, then sending confirmation."""

    if not _is_private_chat(message):
        return

    if command_service is not None:
        profile = _telegram_profile(message)
        if profile is not None:
            await command_service.reset_active_session(
                telegram_user_id=profile["telegram_user_id"],
                telegram_chat_id=profile["telegram_chat_id"],
                username=profile["username"],
                first_name=profile["first_name"],
                language_code=profile["language_code"],
            )
    await message.answer(RESET_MESSAGE)


async def handle_text_message(
    message: TextMessage,
    text_service: TextMessageService | None = None,
) -> None:
    """Handle ordinary text by optionally saving it, then sending a no-DeepSeek placeholder."""

    if not _is_private_chat(message):
        return

    response_text = TEXT_PLACEHOLDER_MESSAGE
    text = message.text
    if text_service is not None and text:
        profile = _telegram_profile(message)
        if profile is not None:
            response_text = await text_service.save_text_message_shell(
                telegram_user_id=profile["telegram_user_id"],
                telegram_chat_id=profile["telegram_chat_id"],
                username=profile["username"],
                first_name=profile["first_name"],
                language_code=profile["language_code"],
                text=text,
                telegram_update_id=cast(int | None, getattr(message, "update_id", None)),
                telegram_message_id=message.message_id,
            )
    await message.answer(response_text)


async def handle_unsupported_message(message: AnswerableMessage) -> None:
    """Handle private unsupported message types with a safe no-service response."""

    if not _is_private_chat(message):
        return

    await message.answer(UNSUPPORTED_MESSAGE)


def _is_private_chat(message: AnswerableMessage) -> bool:
    return _chat_type(message) == "private"


def _chat_type(message: AnswerableMessage) -> str | None:
    return cast(str | None, getattr(message.chat, "type", None))


def _telegram_profile(message: AnswerableMessage) -> CommandProfile | None:
    user = message.from_user
    if user is None:
        return None

    return {
        "telegram_user_id": user.id,
        "telegram_chat_id": message.chat.id,
        "username": user.username,
        "first_name": user.first_name,
        "language_code": user.language_code,
    }
