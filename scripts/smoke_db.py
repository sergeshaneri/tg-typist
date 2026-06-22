"""Safe database smoke check for migrations and basic connectivity."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tg_typist.db.session import create_async_engine  # noqa: E402
from tg_typist.settings import load_settings  # noqa: E402

MigrationRunner = Callable[[Path, Mapping[str, str]], None]
HealthCheck = Callable[[str], None]


def run_migrations_to_head(project_root: Path, env: Mapping[str, str]) -> None:
    """Run Alembic migrations to head using the configured ``DATABASE_URL``."""

    database_url = env.get("DATABASE_URL")
    if database_url is None:
        raise RuntimeError("DATABASE_URL is required to run migrations")

    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        config = Config(str(project_root / "alembic.ini"))
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


async def _run_health_check(database_url: str) -> None:
    """Open an async DB connection and prove a trivial query succeeds."""

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            if result.scalar_one() != 1:
                raise RuntimeError("database health check returned an unexpected result")
    finally:
        await engine.dispose()


def run_health_check(database_url: str) -> None:
    """Run the async database health check from synchronous script code."""

    asyncio.run(_run_health_check(database_url))


def main(
    env: Mapping[str, str] | None = None,
    *,
    migrate: MigrationRunner = run_migrations_to_head,
    health_check: HealthCheck = run_health_check,
) -> int:
    """Run migrations and a minimal DB health query, or skip safely without DB URL."""

    source_env = os.environ if env is None else env
    settings = load_settings(source_env)
    if settings.database_url is None:
        print("db smoke skipped: DATABASE_URL is not set")
        return 0

    migrate(ROOT, source_env)
    health_check(settings.database_url)

    safe_database_url = settings.safe_dict()["database_url"]
    print(f"db smoke passed: migrations=head health=ok database_url={safe_database_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
