"""Opt-in PostgreSQL integration tests for database constraints.

These tests require ``TEST_DATABASE_URL`` to point at an isolated, disposable
PostgreSQL test database. They intentionally do not fall back to ``DATABASE_URL``:
constraint proof may run migrations and delete rows, so using a production-like
application URL by accident would be unsafe.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from tg_typist.db.models import (
    SESSION_STATUS_CLOSED,
    InterviewSession,
    ProcessedTelegramUpdate,
)
from tg_typist.db.repositories import (
    InterviewSessionRepository,
    ProcessedTelegramUpdateRepository,
    TelegramUserRepository,
)
from tg_typist.db.session import create_async_engine, normalize_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_TEST_URL_ENV = "TEST_DATABASE_URL"

pytestmark = pytest.mark.skipif(
    not os.environ.get(POSTGRES_TEST_URL_ENV),
    reason=f"PostgreSQL constraint tests require {POSTGRES_TEST_URL_ENV}",
)


def _postgres_test_url() -> str:
    database_url = os.environ[POSTGRES_TEST_URL_ENV]
    normalized_url = normalize_database_url(database_url)
    if not normalized_url.startswith("postgresql+asyncpg://"):
        pytest.skip(f"{POSTGRES_TEST_URL_ENV} must be a PostgreSQL URL")
    return database_url


@pytest.fixture(scope="module")
def migrated_postgres_database() -> Iterator[str]:
    """Run Alembic head against an explicit disposable PostgreSQL test DB."""

    database_url = _postgres_test_url()
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(config, "head")
        yield database_url
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


@pytest.fixture
async def engine(migrated_postgres_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_database)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM model_calls"))
            await session.execute(text("DELETE FROM messages"))
            await session.execute(text("DELETE FROM processed_telegram_updates"))
            await session.execute(text("DELETE FROM interview_sessions"))
            await session.execute(text("DELETE FROM telegram_users"))
        yield session


async def test_postgres_rejects_two_active_sessions_for_same_user(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=91001,
        telegram_chat_id=92001,
    )
    await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )

    db_session.add(InterviewSession(user_id=user.id, system_prompt_version="duplicate-active"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_postgres_allows_closed_and_active_session_for_same_user(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=91002,
        telegram_chat_id=92002,
    )
    closed_session = InterviewSession(
        user_id=user.id,
        status=SESSION_STATUS_CLOSED,
        reset_reason="closed fixture",
    )
    db_session.add(closed_session)
    await db_session.flush()

    active_session = await InterviewSessionRepository(db_session).get_or_create_active(
        user_id=user.id,
    )

    assert active_session.id != closed_session.id
    assert active_session.status == "active"


async def test_postgres_rejects_duplicate_processed_update_id(
    db_session: AsyncSession,
) -> None:
    update_id = 93001
    db_session.add(ProcessedTelegramUpdate(update_id=update_id, telegram_user_id=91003))
    await db_session.flush()

    db_session.add(ProcessedTelegramUpdate(update_id=update_id, telegram_user_id=99999))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_repositories_remain_compatible_with_postgres_constraints(
    db_session: AsyncSession,
) -> None:
    user = await TelegramUserRepository(db_session).upsert(
        telegram_user_id=91004,
        telegram_chat_id=92004,
    )
    sessions = InterviewSessionRepository(db_session)
    updates = ProcessedTelegramUpdateRepository(db_session)

    initial_session = await sessions.get_or_create_active(user_id=user.id)
    reused_session = await sessions.get_or_create_active(user_id=user.id)
    reset_session = await sessions.reset_active_for_user(
        user_id=user.id,
        reset_reason="postgres constraint fixture",
    )
    accepted_update = await updates.record_received(update_id=93004, telegram_user_id=91004)
    replayed_update = await updates.record_received(update_id=93004, telegram_user_id=99999)

    assert reused_session.id == initial_session.id
    assert initial_session.status == SESSION_STATUS_CLOSED
    assert reset_session.id != initial_session.id
    assert reset_session.status == "active"
    assert accepted_update.created is True
    assert replayed_update.created is False
    assert replayed_update.update.telegram_user_id == 91004


async def test_postgres_allows_one_active_session_per_different_user(
    db_session: AsyncSession,
) -> None:
    users = TelegramUserRepository(db_session)
    first_user = await users.upsert(telegram_user_id=91005, telegram_chat_id=92005)
    second_user = await users.upsert(telegram_user_id=91006, telegram_chat_id=92006)

    db_session.add_all(
        [
            InterviewSession(user_id=first_user.id, id=uuid4()),
            InterviewSession(user_id=second_user.id, id=uuid4()),
        ]
    )
    await db_session.flush()
