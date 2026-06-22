from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _workflow_text() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def test_ci_has_dedicated_postgres_constraints_job() -> None:
    workflow = _workflow_text()

    assert "postgres-constraints:" in workflow
    assert "name: PostgreSQL constraint tests" in workflow
    assert "postgres:" in workflow
    assert "image: postgres:16" in workflow
    assert "--health-cmd" in workflow
    assert "pg_isready -U tg_typist_test -d tg_typist_test" in workflow
    assert "POSTGRES_DB: tg_typist_test" in workflow
    assert "POSTGRES_USER: tg_typist_test" in workflow
    assert "POSTGRES_PASSWORD: postgres" in workflow


def test_ci_runs_opt_in_postgres_constraint_tests_against_service() -> None:
    workflow = _workflow_text()

    assert "TEST_DATABASE_URL:" in workflow
    assert "postgresql://tg_typist_test:postgres@localhost:5432/tg_typist_test" in workflow
    assert (
        "uv run --python 3.12 --extra dev pytest "
        "tests/integration/test_postgres_constraints.py -q"
    ) in workflow
    assert not any(
        line.strip().startswith("DATABASE_URL:") for line in workflow.splitlines()
    )
