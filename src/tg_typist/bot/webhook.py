"""Telegram webhook endpoint shell.

Production requests must present Telegram's webhook secret header. Idempotency
and aiogram dispatch are added by later roadmap tasks; this router still only
acknowledges accepted JSON without external calls.
"""

from __future__ import annotations

from secrets import compare_digest
from typing import Annotated, Any, cast

from fastapi import APIRouter, Header, HTTPException, Request, status

from tg_typist.settings import PRODUCTION_ENVIRONMENT, Settings

TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def telegram_webhook(
    request: Request,
    update: dict[str, Any],
    secret_token: Annotated[str | None, Header(alias=TELEGRAM_SECRET_HEADER)] = None,
) -> dict[str, str]:
    """Accept a Telegram update payload shell without dispatch side effects."""

    _verify_webhook_secret(request, secret_token)
    _ = update
    return {"status": "accepted"}


def _verify_webhook_secret(request: Request, provided_secret: str | None) -> None:
    settings = _get_settings(request)
    if settings.environment != PRODUCTION_ENVIRONMENT:
        return

    expected_secret = settings.telegram_webhook_secret
    if expected_secret is None or provided_secret is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if not compare_digest(provided_secret, expected_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)
