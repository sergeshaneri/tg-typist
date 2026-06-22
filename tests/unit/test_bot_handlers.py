"""Deterministic tests for Telegram command and text handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tg_typist.bot import messages
from tg_typist.bot.handlers import (
    TelegramChatLike,
    TelegramUserLike,
    handle_help,
    handle_privacy,
    handle_reset,
    handle_start,
    handle_text_message,
    handle_unsupported_message,
)
from tg_typist.bot.router import (
    NonCommandTextFilter,
    PrivateUnsupportedMessageFilter,
    command_router,
)


@dataclass(frozen=True)
class FakeUser:
    id: int
    username: str | None = None
    first_name: str | None = None
    language_code: str | None = None


@dataclass(frozen=True)
class FakeChat:
    id: int
    type: str = "private"

class FakeMessage:
    from_user: TelegramUserLike | None
    chat: TelegramChatLike

    def __init__(
        self,
        *,
        chat_type: str = "private",
        text: str | None = "безопасный текст unit-теста",
    ) -> None:
        self.from_user = FakeUser(
            id=42,
            username="typist_test_user",
            first_name="Тест",
            language_code="ru",
        )
        self.chat = FakeChat(id=777, type=chat_type)
        self.text = text
        self.message_id = 888
        self.update_id = 999
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


class FakeCommandService:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.reset: list[dict[str, Any]] = []

    async def ensure_active_session(self, **kwargs: Any) -> None:
        self.started.append(kwargs)

    async def reset_active_session(self, **kwargs: Any) -> None:
        self.reset.append(kwargs)


class FakeTextMessageService:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    async def save_text_message_shell(self, **kwargs: Any) -> str:
        self.saved.append(kwargs)
        return messages.TEXT_PLACEHOLDER_MESSAGE


@pytest.mark.parametrize(
    ("text", "required_substrings"),
    [
        (
            messages.START_MESSAGE,
            ("Привет", "соционического интервью", "/help", "/privacy", "/reset"),
        ),
        (messages.HELP_MESSAGE, ("Команды", "/start", "/help", "/privacy", "/reset")),
        (
            messages.PRIVACY_MESSAGE,
            (
                "сообщения сохраняются",
                "DeepSeek API",
                "старые сессии могут храниться как архив",
                "/reset",
                "удаления или экспорта",
                "политика хранения будет документирована",
            ),
        ),
        (messages.RESET_MESSAGE, ("Активное интервью сброшено", "новую сессию")),
        (
            messages.TEXT_PLACEHOLDER_MESSAGE,
            ("сообщение сохранено", "DeepSeek", "подключен позже"),
        ),
        (
            messages.UNSUPPORTED_MESSAGE,
            ("не поддерживаю", "текстовое сообщение", "команды"),
        ),
        (
            messages.PRIVATE_CHAT_ONLY_MESSAGE,
            ("личных чатах", "не обрабатываю"),
        ),
    ],
)
def test_command_texts_are_russian_utf8_and_include_required_details(
    text: str, required_substrings: tuple[str, ...]
) -> None:
    assert text
    assert text.encode("utf-8").decode("utf-8") == text
    for substring in required_substrings:
        assert substring in text


async def test_start_handler_sends_intro_and_can_ensure_active_session() -> None:
    message = FakeMessage()
    service = FakeCommandService()

    await handle_start(message, command_service=service)

    assert message.answers == [messages.START_MESSAGE]
    assert service.started == [
        {
            "telegram_user_id": 42,
            "telegram_chat_id": 777,
            "username": "typist_test_user",
            "first_name": "Тест",
            "language_code": "ru",
        }
    ]
    assert service.reset == []


async def test_help_handler_sends_help_text_without_side_effects() -> None:
    message = FakeMessage()

    await handle_help(message)

    assert message.answers == [messages.HELP_MESSAGE]


async def test_privacy_handler_sends_privacy_text_without_external_calls() -> None:
    message = FakeMessage()

    await handle_privacy(message)

    assert message.answers == [messages.PRIVACY_MESSAGE]


async def test_reset_handler_sends_reset_text_and_can_reset_active_session() -> None:
    message = FakeMessage()
    service = FakeCommandService()

    await handle_reset(message, command_service=service)

    assert message.answers == [messages.RESET_MESSAGE]
    assert service.reset == [
        {
            "telegram_user_id": 42,
            "telegram_chat_id": 777,
            "username": "typist_test_user",
            "first_name": "Тест",
            "language_code": "ru",
        }
    ]
    assert service.started == []


async def test_group_command_handlers_noop_without_command_service_calls() -> None:
    start_message = FakeMessage(chat_type="group")
    reset_message = FakeMessage(chat_type="supergroup")
    service = FakeCommandService()

    await handle_start(start_message, command_service=service)
    await handle_reset(reset_message, command_service=service)

    assert start_message.answers == []
    assert reset_message.answers == []
    assert service.started == []
    assert service.reset == []


async def test_text_handler_saves_text_when_service_injected_and_sends_placeholder() -> None:
    message = FakeMessage()
    service = FakeTextMessageService()

    await handle_text_message(message, text_service=service)

    assert message.answers == [messages.TEXT_PLACEHOLDER_MESSAGE]
    assert service.saved == [
        {
            "telegram_user_id": 42,
            "telegram_chat_id": 777,
            "username": "typist_test_user",
            "first_name": "Тест",
            "language_code": "ru",
            "text": "безопасный текст unit-теста",
            "telegram_update_id": 999,
            "telegram_message_id": 888,
        }
    ]


async def test_private_text_handler_still_saves_text_when_group_policy_exists() -> None:
    message = FakeMessage(chat_type="private")
    service = FakeTextMessageService()

    await handle_text_message(message, text_service=service)

    assert message.answers == [messages.TEXT_PLACEHOLDER_MESSAGE]
    assert len(service.saved) == 1


async def test_group_text_handler_noops_without_service_or_answer() -> None:
    message = FakeMessage(chat_type="supergroup")
    service = FakeTextMessageService()

    await handle_text_message(message, text_service=service)

    assert message.answers == []
    assert service.saved == []


async def test_private_unsupported_message_gets_safe_response_without_service_calls() -> None:
    message = FakeMessage(text=None)

    await handle_unsupported_message(message)

    assert message.answers == [messages.UNSUPPORTED_MESSAGE]


async def test_group_unsupported_message_noops_to_avoid_group_noise() -> None:
    message = FakeMessage(chat_type="group", text=None)

    await handle_unsupported_message(message)

    assert message.answers == []


async def test_text_handler_without_service_only_sends_placeholder() -> None:
    message = FakeMessage()

    await handle_text_message(message)

    assert message.answers == [messages.TEXT_PLACEHOLDER_MESSAGE]


def test_command_router_registers_command_and_text_handlers() -> None:
    handler_names = {handler.callback.__name__ for handler in command_router.message.handlers}

    assert {"handle_start", "handle_help", "handle_privacy", "handle_reset"}.issubset(handler_names)
    assert "handle_text_message" in handler_names
    assert "handle_unsupported_message" in handler_names
    assert len(command_router.message.handlers) == 6


async def test_non_command_text_filter_accepts_private_text_and_excludes_slash_or_groups() -> None:
    filter_ = NonCommandTextFilter()

    assert await filter_(FakeMessage(text="обычный ответ")) is True  # type: ignore[arg-type]
    assert await filter_(FakeMessage(text="/start")) is False  # type: ignore[arg-type]
    assert await filter_(FakeMessage(chat_type="group", text="обычный ответ")) is False  # type: ignore[arg-type]


async def test_private_unsupported_filter_accepts_only_private_non_text_messages() -> None:
    filter_ = PrivateUnsupportedMessageFilter()

    assert await filter_(FakeMessage(text=None)) is True  # type: ignore[arg-type]
    assert await filter_(FakeMessage(text="обычный ответ")) is False  # type: ignore[arg-type]
    assert await filter_(FakeMessage(chat_type="supergroup", text=None)) is False  # type: ignore[arg-type]
