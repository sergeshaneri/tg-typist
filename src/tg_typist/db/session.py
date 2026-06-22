"""Async SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine as sqlalchemy_create_async_engine

_POSTGRES_SCHEME = "postgres" + "://"
_POSTGRESQL_SCHEME = "postgresql" + "://"
_ASYNCPG_SCHEME = "postgresql+asyncpg" + "://"


def normalize_database_url(database_url: str) -> str:
    """Return a PostgreSQL URL that uses SQLAlchemy's asyncpg driver."""

    if database_url.startswith(_POSTGRES_SCHEME):
        return _ASYNCPG_SCHEME + database_url.removeprefix(_POSTGRES_SCHEME)
    if database_url.startswith(_POSTGRESQL_SCHEME):
        return _ASYNCPG_SCHEME + database_url.removeprefix(_POSTGRESQL_SCHEME)
    return database_url


def create_async_engine(database_url: str) -> AsyncEngine:
    """Create the application async engine without opening a connection."""

    return sqlalchemy_create_async_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for repository and service layers."""

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Open a transaction-scoped async session."""

    async with session_factory() as session:
        async with session.begin():
            yield session
