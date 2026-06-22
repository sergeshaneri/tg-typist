from __future__ import annotations

import configparser
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from tg_typist.db.base import Base
from tg_typist.db.session import create_async_engine, create_session_factory, normalize_database_url

ROOT = Path(__file__).resolve().parents[2]


def test_normalize_database_url_uses_asyncpg_driver() -> None:
    assert (
        normalize_database_url("postgres://user@localhost:5432/tg_typist")
        == "postgresql+asyncpg://user@localhost:5432/tg_typist"
    )
    assert (
        normalize_database_url("postgresql://user@localhost/tg_typist")
        == "postgresql+asyncpg://user@localhost/tg_typist"
    )
    assert (
        normalize_database_url("postgresql+asyncpg://user@localhost/tg_typist")
        == "postgresql+asyncpg://user@localhost/tg_typist"
    )


def test_create_async_engine_uses_asyncpg_and_pre_ping() -> None:
    engine = create_async_engine("postgresql://user@localhost:5432/tg_typist")

    try:
        assert engine.url.drivername == "postgresql+asyncpg"
        assert engine.pool._pre_ping is True  # noqa: SLF001 - validating engine setup contract
    finally:
        # No connection was opened, but dispose keeps the test lifecycle explicit.
        engine.sync_engine.dispose()


def test_create_session_factory_returns_async_sessions_without_expiring_on_commit() -> None:
    engine = create_async_engine("postgresql://user@localhost:5432/tg_typist")

    try:
        session_factory = create_session_factory(engine)

        assert session_factory.class_ is AsyncSession
        assert session_factory.kw["expire_on_commit"] is False
    finally:
        engine.sync_engine.dispose()


def test_declarative_base_has_naming_convention_for_migrations() -> None:
    convention = Base.metadata.naming_convention

    assert convention["ix"] == "ix_%(column_0_label)s"
    assert convention["pk"] == "pk_%(table_name)s"
    assert "fk" in convention


def test_alembic_config_points_to_repo_migrations() -> None:
    config = configparser.ConfigParser()
    config.read(ROOT / "alembic.ini", encoding="utf-8")

    assert config["alembic"]["script_location"] == "src/tg_typist/db/migrations"
    assert (ROOT / "src/tg_typist/db/migrations/env.py").exists()
    assert (ROOT / "src/tg_typist/db/migrations/versions").is_dir()
