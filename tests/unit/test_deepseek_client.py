"""DeepSeek HTTP client tests with mocked provider calls."""

from __future__ import annotations

import json

import httpx
import respx

from tg_typist.llm.deepseek import (
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekClient,
    DeepSeekFailure,
    DeepSeekSuccess,
)
from tg_typist.llm.errors import (
    DEEPSEEK_ERROR_AUTHENTICATION,
    DEEPSEEK_ERROR_INVALID_RESPONSE,
    DEEPSEEK_ERROR_MISSING_API_KEY,
    DEEPSEEK_ERROR_PROVIDER,
    DEEPSEEK_ERROR_TIMEOUT,
)
from tg_typist.llm.history import LLMMessage
from tg_typist.settings import load_settings


def prompt_messages() -> tuple[LLMMessage, ...]:
    return (
        LLMMessage(role="system", content="system rules"),
        LLMMessage(role="user", content="safe user text"),
    )


def success_body() -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1,
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "assistant answer"},
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


def test_default_model_matches_verified_deepseek_docs() -> None:
    client = DeepSeekClient(api_key="test-key")

    assert client.model == DEFAULT_DEEPSEEK_MODEL
    assert client.model == "deepseek-v4-flash"


@respx.mock
async def test_complete_posts_configured_model_messages_and_auth_header() -> None:
    route = respx.post("https://deepseek.test/chat/completions").mock(
        return_value=httpx.Response(200, json=success_body())
    )
    settings = load_settings(
        {
            "ENVIRONMENT": "test",
            "DEEPSEEK_API_KEY": "test-deepseek-key",
            "DEEPSEEK_BASE_URL": "https://deepseek.test",
            "DEEPSEEK_MODEL": "deepseek-v4-pro",
        }
    )
    client = DeepSeekClient.from_settings(settings)

    result = await client.complete(prompt_messages())

    assert isinstance(result, DeepSeekSuccess)
    assert result.text == "assistant answer"
    assert result.model == "deepseek-v4-flash"
    assert result.finish_reason == "stop"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5
    assert result.total_tokens == 15
    assert result.latency_ms >= 0
    assert route.called
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer test-deepseek-key"
    assert json.loads(request.content) == {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": "system rules"},
            {"role": "user", "content": "safe user text"},
        ],
        "stream": False,
    }


@respx.mock
async def test_missing_api_key_returns_typed_error_without_http_call() -> None:
    route = respx.post("https://deepseek.test/chat/completions").mock(
        return_value=httpx.Response(200, json=success_body())
    )
    settings = load_settings(
        {
            "ENVIRONMENT": "test",
            "DEEPSEEK_BASE_URL": "https://deepseek.test",
        }
    )
    client = DeepSeekClient.from_settings(settings)

    result = await client.complete(prompt_messages())

    assert isinstance(result, DeepSeekFailure)
    assert result.error.code == DEEPSEEK_ERROR_MISSING_API_KEY
    assert result.error.retryable is False
    assert route.called is False


async def test_timeout_is_retried_then_returns_timeout_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.test",
    ) as http_client:
        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://deepseek.test",
            max_retries=2,
            http_client=http_client,
        )
        result = await client.complete(prompt_messages())

    assert calls == 3
    assert isinstance(result, DeepSeekFailure)
    assert result.error.code == DEEPSEEK_ERROR_TIMEOUT
    assert result.error.retryable is True
    assert result.latency_ms >= 0


async def test_retryable_http_error_retries_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": {"message": "overloaded"}})
        return httpx.Response(200, json=success_body())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.test",
    ) as http_client:
        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://deepseek.test",
            max_retries=2,
            http_client=http_client,
        )
        result = await client.complete(prompt_messages())

    assert calls == 2
    assert isinstance(result, DeepSeekSuccess)
    assert result.text == "assistant answer"


async def test_authentication_error_is_not_retried_and_redacts_api_key() -> None:
    calls = 0
    api_key = "deepseek-secret-key"

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            json={"error": {"message": f"bad key {api_key}"}},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.test",
    ) as http_client:
        client = DeepSeekClient(
            api_key=api_key,
            base_url="https://deepseek.test",
            max_retries=2,
            http_client=http_client,
        )
        result = await client.complete(
            (
                LLMMessage(role="system", content="system"),
                LLMMessage(role="user", content="SECRET USER TEXT MUST NOT LEAK"),
            )
        )

    assert calls == 1
    assert isinstance(result, DeepSeekFailure)
    assert result.error.code == DEEPSEEK_ERROR_AUTHENTICATION
    assert result.error.retryable is False
    assert api_key not in result.error.message_redacted
    assert "SECRET USER TEXT MUST NOT LEAK" not in result.error.message_redacted


async def test_invalid_success_shape_returns_typed_error() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={})),
        base_url="https://deepseek.test",
    ) as http_client:
        client = DeepSeekClient(api_key="test-key", http_client=http_client)
        result = await client.complete(prompt_messages())

    assert isinstance(result, DeepSeekFailure)
    assert result.error.code == DEEPSEEK_ERROR_INVALID_RESPONSE
    assert result.error.retryable is False


async def test_exhausted_server_errors_return_provider_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"error": {"message": "server failed"}})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.test",
    ) as http_client:
        client = DeepSeekClient(
            api_key="test-key",
            max_retries=1,
            http_client=http_client,
        )
        result = await client.complete(prompt_messages())

    assert calls == 2
    assert isinstance(result, DeepSeekFailure)
    assert result.error.code == DEEPSEEK_ERROR_PROVIDER
    assert result.error.retryable is True
