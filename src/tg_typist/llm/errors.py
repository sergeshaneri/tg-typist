"""Typed LLM adapter error contracts."""

from __future__ import annotations

from dataclasses import dataclass

DEEPSEEK_ERROR_AUTHENTICATION = "authentication_error"
DEEPSEEK_ERROR_INSUFFICIENT_BALANCE = "insufficient_balance"
DEEPSEEK_ERROR_INVALID_RESPONSE = "invalid_response"
DEEPSEEK_ERROR_INVALID_REQUEST = "invalid_request"
DEEPSEEK_ERROR_MISSING_API_KEY = "missing_api_key"
DEEPSEEK_ERROR_PROVIDER = "provider_error"
DEEPSEEK_ERROR_RATE_LIMIT = "rate_limit"
DEEPSEEK_ERROR_TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class DeepSeekError:
    """Provider error safe to persist without raw prompt or secrets."""

    code: str
    message_redacted: str
    status_code: int | None = None
    retryable: bool = False
