"""DeepSeek chat-completions HTTP adapter."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

import httpx

from tg_typist.llm.errors import (
    DEEPSEEK_ERROR_AUTHENTICATION,
    DEEPSEEK_ERROR_INSUFFICIENT_BALANCE,
    DEEPSEEK_ERROR_INVALID_REQUEST,
    DEEPSEEK_ERROR_INVALID_RESPONSE,
    DEEPSEEK_ERROR_MISSING_API_KEY,
    DEEPSEEK_ERROR_PROVIDER,
    DEEPSEEK_ERROR_RATE_LIMIT,
    DEEPSEEK_ERROR_TIMEOUT,
    DeepSeekError,
)
from tg_typist.llm.history import LLMMessage
from tg_typist.settings import Settings

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
CHAT_COMPLETIONS_PATH = "/chat/completions"

_RETRYABLE_STATUS_CODES = {429, 500, 503}


@dataclass(frozen=True, slots=True)
class DeepSeekSuccess:
    """Successful provider response parsed for persistence and Telegram output."""

    text: str
    model: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int


@dataclass(frozen=True, slots=True)
class DeepSeekFailure:
    """Failed provider response without raw prompt or secrets."""

    error: DeepSeekError
    latency_ms: int


DeepSeekResult = DeepSeekSuccess | DeepSeekFailure


class DeepSeekClient:
    """Small async client for DeepSeek's OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model or DEFAULT_DEEPSEEK_MODEL
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._http_client = http_client

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> DeepSeekClient:
        """Create a client from application settings without opening a connection."""

        return cls(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            timeout_seconds=settings.deepseek_timeout_seconds,
            max_retries=settings.deepseek_max_retries,
            http_client=http_client,
        )

    @property
    def model(self) -> str:
        """Return the model this client sends to DeepSeek."""

        return self._model

    async def complete(self, messages: Sequence[LLMMessage]) -> DeepSeekResult:
        """Request one non-streaming chat completion."""

        started_at = perf_counter()
        if self._api_key is None:
            return DeepSeekFailure(
                error=DeepSeekError(
                    code=DEEPSEEK_ERROR_MISSING_API_KEY,
                    message_redacted="DeepSeek API key is not configured",
                    retryable=False,
                ),
                latency_ms=_elapsed_ms(started_at),
            )
        api_key = self._api_key

        payload = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        attempts = self._max_retries + 1
        for attempt_index in range(attempts):
            response_or_error = await self._post(payload, headers)
            if isinstance(response_or_error, DeepSeekFailure):
                if attempt_index < self._max_retries and response_or_error.error.retryable:
                    continue
                return DeepSeekFailure(
                    error=response_or_error.error,
                    latency_ms=_elapsed_ms(started_at),
                )

            if response_or_error.status_code == httpx.codes.OK:
                return _parse_success_response(response_or_error, _elapsed_ms(started_at))

            error = _parse_error_response(response_or_error, api_key)
            if attempt_index < self._max_retries and error.retryable:
                continue
            return DeepSeekFailure(error=error, latency_ms=_elapsed_ms(started_at))

        return DeepSeekFailure(
            error=DeepSeekError(
                code=DEEPSEEK_ERROR_PROVIDER,
                message_redacted="DeepSeek request failed",
                retryable=True,
            ),
            latency_ms=_elapsed_ms(started_at),
        )

    async def _post(
        self,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response | DeepSeekFailure:
        try:
            if self._http_client is not None:
                return await self._http_client.post(
                    CHAT_COMPLETIONS_PATH,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )

            async with httpx.AsyncClient(base_url=self._base_url) as client:
                return await client.post(
                    CHAT_COMPLETIONS_PATH,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
        except httpx.TimeoutException:
            return DeepSeekFailure(
                error=DeepSeekError(
                    code=DEEPSEEK_ERROR_TIMEOUT,
                    message_redacted="DeepSeek request timed out",
                    retryable=True,
                ),
                latency_ms=0,
            )
        except httpx.HTTPError:
            return DeepSeekFailure(
                error=DeepSeekError(
                    code=DEEPSEEK_ERROR_PROVIDER,
                    message_redacted="DeepSeek request failed",
                    retryable=True,
                ),
                latency_ms=0,
            )


def _parse_success_response(response: httpx.Response, latency_ms: int) -> DeepSeekResult:
    try:
        data = response.json()
        choices = _as_list(data.get("choices"))
        first_choice = _as_dict(choices[0])
        message = _as_dict(first_choice.get("message"))
        content = message.get("content")
        usage = _as_dict(data.get("usage"))
    except (IndexError, TypeError, ValueError, AttributeError):
        return DeepSeekFailure(
            error=DeepSeekError(
                code=DEEPSEEK_ERROR_INVALID_RESPONSE,
                message_redacted="DeepSeek response shape was invalid",
                status_code=response.status_code,
            ),
            latency_ms=latency_ms,
        )

    if not isinstance(content, str) or not content:
        return DeepSeekFailure(
            error=DeepSeekError(
                code=DEEPSEEK_ERROR_INVALID_RESPONSE,
                message_redacted="DeepSeek response did not include assistant content",
                status_code=response.status_code,
            ),
            latency_ms=latency_ms,
        )

    return DeepSeekSuccess(
        text=content,
        model=_optional_str(data.get("model")) or "",
        finish_reason=_optional_str(first_choice.get("finish_reason")),
        prompt_tokens=_optional_int(usage.get("prompt_tokens")),
        completion_tokens=_optional_int(usage.get("completion_tokens")),
        total_tokens=_optional_int(usage.get("total_tokens")),
        latency_ms=latency_ms,
    )


def _parse_error_response(response: httpx.Response, api_key: str) -> DeepSeekError:
    status_code = response.status_code
    return DeepSeekError(
        code=_error_code_for_status(status_code),
        message_redacted=_redacted_error_message(response, api_key),
        status_code=status_code,
        retryable=status_code in _RETRYABLE_STATUS_CODES,
    )


def _error_code_for_status(status_code: int) -> str:
    if status_code == httpx.codes.UNAUTHORIZED:
        return DEEPSEEK_ERROR_AUTHENTICATION
    if status_code == httpx.codes.PAYMENT_REQUIRED:
        return DEEPSEEK_ERROR_INSUFFICIENT_BALANCE
    if status_code == httpx.codes.TOO_MANY_REQUESTS:
        return DEEPSEEK_ERROR_RATE_LIMIT
    if status_code in (httpx.codes.BAD_REQUEST, httpx.codes.UNPROCESSABLE_ENTITY):
        return DEEPSEEK_ERROR_INVALID_REQUEST
    return DEEPSEEK_ERROR_PROVIDER


def _redacted_error_message(response: httpx.Response, api_key: str) -> str:
    try:
        data = response.json()
    except ValueError:
        return f"DeepSeek request failed with status {response.status_code}"

    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message.replace(api_key, "***")[:500]
    return f"DeepSeek request failed with status {response.status_code}"


def _as_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("expected object")
    return cast(dict[str, Any], value)


def _as_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError("expected list")
    return value


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))
