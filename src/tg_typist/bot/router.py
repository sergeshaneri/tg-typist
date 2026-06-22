"""Aiogram router for Telegram command and text handlers."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message

from tg_typist.bot.handlers import (
    handle_help,
    handle_privacy,
    handle_reset,
    handle_start,
    handle_text_message,
    handle_unsupported_message,
)


class NonCommandTextFilter(BaseFilter):
    """Match private ordinary text while leaving slash commands to command handlers."""

    async def __call__(self, message: Message) -> bool:
        text = message.text
        return _is_private_message(message) and bool(text and not text.strip().startswith("/"))


class PrivateUnsupportedMessageFilter(BaseFilter):
    """Match private non-text messages for the unsupported-message fallback."""

    async def __call__(self, message: Message) -> bool:
        return _is_private_message(message) and message.text is None


def _is_private_message(message: Message) -> bool:
    return getattr(message.chat, "type", None) == "private"


command_router = Router(name="telegram_commands")
command_router.message.register(handle_start, Command("start"))
command_router.message.register(handle_help, Command("help"))
command_router.message.register(handle_privacy, Command("privacy"))
command_router.message.register(handle_reset, Command("reset"))
command_router.message.register(handle_text_message, NonCommandTextFilter())
command_router.message.register(handle_unsupported_message, PrivateUnsupportedMessageFilter())

__all__ = ["NonCommandTextFilter", "PrivateUnsupportedMessageFilter", "command_router"]
