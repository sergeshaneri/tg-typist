"""Telegram webhook endpoint shell.

Production requests must present Telegram's webhook secret header. The endpoint
records Telegram update IDs before future dispatch work so retries can be
acknowledged without repeating side effects.
"""

from __future__ import annotations

from secrets import compare_digest
from typing import Annotated, Any, TypedDict, cast

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tg_typist.db.repositories import ProcessedTelegramUpdateRepository
from tg_typist.db.session import session_scope
from tg_typist.settings import PRODUCTION_ENVIRONMENT, Settings

TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"

router = APIRouter(prefix="/telegram", tags=["telegram"])


class UpdateMetadata(TypedDict):
    """Metadata safe to store for Telegram update idempotency."""

    update_id: int
    telegram_user_id: int | None
    telegram_chat_id: int | None
    telegram_message_id: int | None


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def telegram_webhook(
    request: Request,
    update: dict[str, Any],
    secret_token: Annotated[str | None, Header(alias=TELEGRAM_SECRET_HEADER)] = None,
) -> dict[str, str]:
    """Accept a Telegram update payload shell without dispatch side effects."""

    _verify_webhook_secret(request, secret_token)
    update_metadata = _extract_update_metadata(update)
    session_factory = _get_session_factory(request)
    if session_factory is not None:
        async with session_scope(session_factory) as db_session:
            updates = ProcessedTelegramUpdateRepository(db_session)
            record = await updates.record_received(**update_metadata)
            if not record.created:
                return {"status": "duplicate"}
            await updates.mark_processed(update_metadata["update_id"])
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


def _get_session_factory(request: Request) -> async_sessionmaker[AsyncSession] | None:
    return cast(
        async_sessionmaker[AsyncSession] | None,
        getattr(request.app.state, "session_factory", None),
    )


def _extract_update_metadata(update: dict[str, Any]) -> UpdateMetadata:
    update_id = update.get("update_id")
    if not isinstance(update_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid update_id")

    message = _extract_message(update)
    from_user = _dict_or_empty(message.get("from"))
    chat = _dict_or_empty(message.get("chat"))

    return {
        "update_id": update_id,
        "telegram_user_id": _optional_int(from_user.get("id")),
        "telegram_chat_id": _optional_int(chat.get("id")),
        "telegram_message_id": _optional_int(message.get("message_id")),
    }


def _extract_message(update: dict[str, Any]) -> dict[str, Any]:
    for field_name in ("message", "edited_message", "channel_post", "edited_channel_post"):
        message = update.get(field_name)
        if isinstance(message, dict):
            return cast(dict[str, Any], message)
    return {}


def _dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None
