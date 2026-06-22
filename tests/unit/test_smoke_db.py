from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SMOKE_DB_PATH = ROOT / "scripts" / "smoke_db.py"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_missing_database_url_skips_explicitly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_db = _load_module(SMOKE_DB_PATH, "smoke_db_skip_under_test")

    exit_code = smoke_db.main({"ENVIRONMENT": "test"})

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "db smoke skipped: DATABASE_URL is not set"
    assert captured.err == ""


def test_configured_database_runs_migrations_and_health_without_leaking_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_db = _load_module(SMOKE_DB_PATH, "smoke_db_success_under_test")
    calls: list[tuple[str, str]] = []
    raw_url = "postgresql://db_user:super-secret-password@localhost:5432/tg_typist"

    def fake_migrate(project_root: Path, env: Mapping[str, str]) -> None:
        assert project_root == ROOT
        assert env["DATABASE_URL"] == raw_url
        calls.append(("migrate", env["DATABASE_URL"]))

    def fake_health(database_url: str) -> None:
        calls.append(("health", database_url))

    exit_code = smoke_db.main(
        {"ENVIRONMENT": "test", "DATABASE_URL": raw_url},
        migrate=fake_migrate,
        health_check=fake_health,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [("migrate", raw_url), ("health", raw_url)]
    assert "db smoke passed" in captured.out
    assert "database_url=postgresql://db_user:***@localhost:5432/tg_typist" in captured.out
    assert "super-secret-password" not in captured.out
    assert raw_url not in captured.out
    assert captured.err == ""
