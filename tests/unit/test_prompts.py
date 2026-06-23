from __future__ import annotations

import os
from importlib import resources

import pytest

from tg_typist.llm.prompts import (
    DEFAULT_SYSTEM_PROMPT_RESOURCE,
    SYSTEM_PROMPT_VERSION,
    PromptLoadError,
    SystemPrompt,
    load_system_prompt,
)


def test_default_system_prompt_loads_versioned_non_empty_text() -> None:
    prompt = load_system_prompt()

    assert isinstance(prompt, SystemPrompt)
    assert prompt.version == SYSTEM_PROMPT_VERSION
    assert prompt.version == "typist_all_in_one_reinin_v1"
    assert prompt.text.strip()
    assert len(prompt.text) > 15_000


def test_default_system_prompt_is_utf8_all_in_one_reinin_prompt() -> None:
    prompt = load_system_prompt()

    assert "Вы — соционический бот" in prompt.text
    assert "Сбор общих сведений" in prompt.text
    assert "Диагностика по Признакам Рейнина" in prompt.text
    assert "СТРОГО в следующем порядке" in prompt.text
    assert "Задавайте по ОДНОМУ вопросу в ОДНОМ сообщении" in prompt.text


def test_missing_system_prompt_resource_raises_clear_error() -> None:
    missing_name = "missing_typist_system.md"

    with pytest.raises(PromptLoadError) as exc_info:
        load_system_prompt(resource_name=missing_name)

    message = str(exc_info.value)
    assert missing_name in message
    assert "system prompt resource not found" in message
    assert "DATABASE_URL" not in message
    assert "DEEPSEEK" not in message
    assert "TELEGRAM" not in message
    assert ":\\" not in message
    assert "/c/Users" not in message


def test_system_prompt_loader_does_not_require_environment_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in tuple(os.environ):
        if name.startswith(("TELEGRAM", "DEEPSEEK", "DATABASE")):
            monkeypatch.delenv(name, raising=False)

    prompt = load_system_prompt(resource_name=DEFAULT_SYSTEM_PROMPT_RESOURCE)

    assert prompt.version == SYSTEM_PROMPT_VERSION
    assert "Вы — соционический бот" in prompt.text


def test_future_one_sign_prompts_are_available_as_utf8_resources() -> None:
    prompt_root = resources.files("tg_typist.prompts")
    irrationality = prompt_root.joinpath("future/01-irrationality-rationality.md").read_text(
        encoding="utf-8"
    )
    extroversion = prompt_root.joinpath("future/02-extroversion-introversion.md").read_text(
        encoding="utf-8"
    )

    assert "Рациональность/Иррациональность" in irrationality
    assert "Экстраверсия/Интроверсия" in extroversion
    assert "Один вопрос за раз" in irrationality
    assert "v2" in extroversion
