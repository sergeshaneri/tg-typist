from __future__ import annotations

import os

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
    assert prompt.version == "typist_system_v1"
    assert prompt.text.strip()
    assert len(prompt.text) > 100


def test_default_system_prompt_is_utf8_russian_placeholder() -> None:
    prompt = load_system_prompt()

    assert "соционическое интервью" in prompt.text
    assert "краткие уточняющие вопросы" in prompt.text
    assert "не делай финальный вывод" in prompt.text
    assert "внешних инструментов" in prompt.text
    assert "плейсхолдер" in prompt.text.lower()


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
    assert "соционическое интервью" in prompt.text
