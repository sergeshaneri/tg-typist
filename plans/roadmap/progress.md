# Roadmap Progress

## Snapshot

- Created: 2026-06-20.
- Current repository state: application scaffold, database foundation, FastAPI webhook shell with production secret verification, deterministic aiogram command handlers, no-DeepSeek text-message persistence shell, and a versioned bundled system-prompt loader are in place; PostgreSQL-specific proof is wired into CI and awaits a real GitHub Actions run.
- Current product target: Telegram bot on Railway with Railway PostgreSQL and DeepSeek API.
- MVP history policy: send full active-session conversation to DeepSeek.
- Validation: `scripts/validate.py` runs compile, Ruff, mypy, unit tests, config smoke and safely-skipping DB smoke.

## Current Status

| Area | Status | Notes |
|---|---:|---|
| Roadmap artifacts | DONE | PRD, architecture, domain model, deployment, security checklist, tasks and handoff created. |
| Application scaffold | DONE | Python project scaffold and dependency metadata created. |
| Database | BLOCKED | Async SQLAlchemy engine/session, core schema/models, repository layer and DB smoke are added; model/migration encode active-session and processed-update uniqueness, but real PostgreSQL constraint proof awaits an actual CI PostgreSQL run or local `TEST_DATABASE_URL`. |
| Telegram integration | IN PROGRESS | FastAPI app factory, `/health`, Telegram webhook shell, production secret verification, aiogram command handlers, text-message persistence shell, private-chat MVP policy and unsupported-message fallback are in place; idempotency, webhook dispatch and full DeepSeek text processing remain planned. |
| DeepSeek integration | IN PROGRESS | Versioned bundled system-prompt loader and initial typist prompt placeholder are in place; history builder, adapter, context-limit handling and model-call integration remain planned. |
| Railway deployment | TODO | Deployment docs planned. |
| GitHub CI | DONE | `.github/workflows/ci.yml` runs the local validation gate without live secrets and has a dedicated PostgreSQL service job for opt-in constraint tests. |
| Future orchestrator | TODO | Out of MVP, but schema will preserve extension points. |

## Recommended Next Step

Continue with `L4.2` for the history builder while `T3.3` waits on blocked `D2.6`; also monitor the next GitHub Actions run, then recheck `D2.6` and mark it DONE if the PostgreSQL constraint tests pass against the real service.

## Milestone Checklist

- [x] `AGENTS.md`
- [x] `harness/README.md`
- [x] `harness/failure-log.md`
- [x] `plans/README.md`
- [x] `plans/roadmap/PRD.md`
- [x] `plans/roadmap/domain-model.md`
- [x] `plans/roadmap/architecture.md`
- [x] `plans/roadmap/deployment.md`
- [x] `plans/roadmap/security-checklist.md`
- [x] `plans/roadmap/decisions.md`
- [x] `plans/roadmap/invariant-checklist.md`
- [x] `plans/roadmap/task-template.md`
- [x] `plans/roadmap/handoff.md`
- [x] `plans/roadmap/tasks.md`
- [x] docs readback check

## Change Log

### 2026-06-20 - Task H0.1

- Status: DONE
- Changed files:
  - `AGENTS.md`
  - `harness/README.md`
  - `harness/failure-log.md`
  - `plans/README.md`
  - `plans/roadmap/PRD.md`
  - `plans/roadmap/domain-model.md`
  - `plans/roadmap/architecture.md`
  - `plans/roadmap/deployment.md`
  - `plans/roadmap/security-checklist.md`
  - `plans/roadmap/decisions.md`
  - `plans/roadmap/invariant-checklist.md`
  - `plans/roadmap/task-template.md`
  - `plans/roadmap/handoff.md`
  - `plans/roadmap/progress.md`
  - `plans/roadmap/tasks.md`
- Summary:
  - Created repo-local planning harness modeled after the reference project.
  - Captured the MVP as a single-prompt Telegram bot using DeepSeek and Railway PostgreSQL.
  - Recorded initial decisions for Python async stack, webhook deployment, full active-session history and mocked external tests.
- Checks:
  - `rg --files`: passed
  - UTF-8 readback of `AGENTS.md`, `plans/roadmap/tasks.md` and `plans/roadmap/progress.md`: passed
- Decisions:
  - `DEC-001`
  - `DEC-002`
  - `DEC-003`
  - `DEC-004`
  - `DEC-005`
- Remaining:
  - none

### 2026-06-20 - Plan best-practices review update

- Status: DONE
- Changed files:
  - `plans/roadmap/PRD.md`
  - `plans/roadmap/architecture.md`
  - `plans/roadmap/domain-model.md`
  - `plans/roadmap/security-checklist.md`
  - `plans/roadmap/deployment.md`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/invariant-checklist.md`
  - `plans/roadmap/decisions.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added Telegram webhook idempotency as a first-class MVP requirement.
  - Required PostgreSQL constraints for one active session per user and unique processed updates.
  - Required real PostgreSQL migration/repository tests for DB-specific behavior.
  - Added Railway `PORT` binding to settings and deployment acceptance.
  - Clarified DeepSeek model defaults must be checked against current official docs and deprecated aliases should not be defaults.
  - Promoted privacy deletion and retention policy from later release concern into MVP/external-testing gates.
  - Documented one-replica MVP assumption unless distributed locking is added.
- Checks:
  - UTF-8 readback/search across updated roadmap files for idempotency, PostgreSQL constraints, Railway `PORT`, DeepSeek model defaults and retention policy: passed
- Decisions:
  - `DEC-006`
  - `DEC-007`
  - `DEC-008`
  - `DEC-009`
  - `DEC-010`
- Remaining:
  - none

### 2026-06-20 - Task S1.1

- Status: DONE
- Changed files:
  - `pyproject.toml`
  - `src/tg_typist/__init__.py`
  - `.gitignore`
  - `.env.example`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Created the Python project metadata with Python 3.12+ and the async MVP dependency set from `DEC-001`.
  - Added the initial `src/tg_typist` package.
  - Added local ignore rules for Python artifacts, virtualenvs and `.env` files.
  - Added `.env.example` with placeholder-only configuration values.
- Checks:
  - `python -m compileall -q src`: passed using `C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe`
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-20 - Task S1.2

- Status: DONE
- Changed files:
  - `src/tg_typist/settings.py`
  - `tests/__init__.py`
  - `tests/unit/__init__.py`
  - `tests/unit/test_settings.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added environment-backed settings parsing for Telegram, DeepSeek, database, Railway `PORT`, logging, admin IDs and numeric limits.
  - Added production fail-fast validation for required secrets while allowing `ENVIRONMENT=test` to run without live Telegram, DeepSeek or database credentials.
  - Added safe config output and repr redaction for tokens, API keys, webhook secrets and database passwords.
  - Added deterministic unit tests covering required env behavior, test defaults, port handling, numeric validation, admin ID parsing and redaction.
- Checks:
  - `.venv\Scripts\python.exe -m compileall -q src tests`: passed
  - `.venv\Scripts\python.exe -m pytest tests/unit/test_settings.py`: passed, 13 tests
  - `python scripts/validate.py`: not run, `scripts/validate.py` does not exist yet
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-20 - Task S1.3

- Status: DONE
- Changed files:
  - `src/tg_typist/logging.py`
  - `tests/unit/test_logging.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added a stdlib-backed structured logger adapter with JSON formatting.
  - Added redaction for token/key/secret/password-like fields, Authorization headers and database URL passwords.
  - Suppressed full `message`, `prompt`, `text` and `content` payload fields from default structured logs.
  - Added unit tests proving Telegram token, DeepSeek key, DB URL password, Authorization header and full text/prompt fields do not leak.
- Checks:
  - `.venv\Scripts\python.exe -m pytest tests/unit/test_logging.py`: passed, 4 tests
  - `.venv\Scripts\python.exe -m compileall -q src tests`: passed
  - `.venv\Scripts\python.exe -m pytest tests/unit/test_settings.py`: passed, 13 tests
  - `python scripts/validate.py`: not run, `scripts/validate.py` does not exist yet
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-21 - Task S1.4

- Status: DONE
- Changed files:
  - `scripts/validate.py`
  - `scripts/smoke_config.py`
  - `tests/unit/test_validate_script.py`
  - `src/tg_typist/settings.py`
  - `src/tg_typist/logging.py`
  - `tests/unit/test_settings.py`
  - `tests/unit/test_logging.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
  - `uv.lock`
- Summary:
  - Added the staged validation gate with compile, Ruff, mypy, unit-test and config-smoke steps.
  - Added a config smoke script that loads test settings without live Telegram, DeepSeek or database credentials.
  - Added unit coverage for validation step order, commands and config-smoke redaction.
  - Applied Ruff-compatible import formatting and typed pytest fixture annotations so the new gate passes on the existing scaffold.
- Checks:
  - `uv run --python 3.12 --extra dev pytest tests/unit/test_validate_script.py -q`: passed, 3 tests
  - `uv run --python 3.12 --extra dev mypy src tests`: passed
  - `uv run --python 3.12 --extra dev pytest tests/unit -q`: passed, 20 tests
  - `uv run --python 3.12 --extra dev python scripts/validate.py`: passed
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-21 - Task S1.5

- Status: DONE
- Changed files:
  - `.github/workflows/ci.yml`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added a GitHub Actions CI workflow for pushes, pull requests and manual dispatch.
  - The workflow sets up Python 3.12, installs `uv`, and runs the same deterministic local validation gate.
  - CI uses `ENVIRONMENT=test` and does not require Telegram, DeepSeek or database secrets.
- Checks:
  - `uv run --python 3.12 --extra dev python scripts/validate.py`: passed
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-21 - Task D2.1

- Status: DONE
- Changed files:
  - `alembic.ini`
  - `src/tg_typist/db/__init__.py`
  - `src/tg_typist/db/base.py`
  - `src/tg_typist/db/session.py`
  - `src/tg_typist/db/migrations/env.py`
  - `src/tg_typist/db/migrations/versions/.keep`
  - `tests/unit/test_db_session.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added SQLAlchemy declarative base with deterministic naming conventions for Alembic migrations.
  - Added async engine/session factory helpers with PostgreSQL URL normalization to the asyncpg driver.
  - Added Alembic configuration and async migration environment that reads `DATABASE_URL` through app settings.
  - Added unit tests covering URL normalization, engine setup, session factory settings, metadata naming conventions and migration paths.
- Checks:
  - `uv run --python 3.12 --extra dev pytest tests/unit/test_db_session.py -q`: passed, 5 tests
  - `uv run --python 3.12 --extra dev ruff check . --fix`: passed
  - `uv run --python 3.12 --extra dev mypy src tests`: passed
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-21 - Task D2.2

- Status: DONE
- Changed files:
  - `src/tg_typist/db/models.py`
  - `src/tg_typist/db/migrations/env.py`
  - `src/tg_typist/db/migrations/versions/20260621_0001_create_core_tables.py`
  - `tests/unit/test_db_models.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added core SQLAlchemy models for Telegram users, interview sessions, processed Telegram updates, messages and model-call metadata.
  - Added uniqueness/idempotency constraints for Telegram user IDs and Telegram update IDs.
  - Added PostgreSQL partial unique index for one active interview session per user.
  - Added the initial Alembic migration for all core persistence tables and indexes.
  - Added unit tests for metadata registration, constraints, foreign keys, MVP defaults, migration contents and PostgreSQL DDL compilation.
- Checks:
  - `uv run --python 3.12 --extra dev pytest tests/unit/test_db_models.py -q`: passed, 7 tests
  - `uv run --python 3.12 --extra dev ruff check . --fix`: passed
  - `uv run --python 3.12 --extra dev mypy src tests`: passed
- Decisions:
  - none
- Remaining:
  - none

### 2026-06-21 - Task D2.3

- Status: DONE
- Changed files:
  - `src/tg_typist/db/repositories.py`
  - `tests/integration/__init__.py`
  - `tests/integration/test_repositories.py`
  - `pyproject.toml`
  - `uv.lock`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added async SQLAlchemy repositories for Telegram user upsert, active-session get/create, Telegram update idempotency records, user/assistant message persistence and model-call metadata updates.
  - Added deterministic local repository integration tests using SQLite via `aiosqlite`; these tests cover repository behavior only and do not claim PostgreSQL partial-index concurrency coverage.
  - Added `aiosqlite` to the dev extra so local async repository tests run without live PostgreSQL, Telegram or DeepSeek.
- Checks:
  - `uv run --python 3.12 --extra dev pytest tests/integration/test_repositories.py -q`: passed, 4 tests
  - `uv run --python 3.12 --extra dev pytest tests/unit/test_db_models.py -q`: passed, 7 tests
  - `uv run --python 3.12 --extra dev ruff check . --fix`: passed
  - `uv run --python 3.12 --extra dev ruff check .`: passed
  - `uv run --python 3.12 --extra dev mypy src tests`: passed
  - `uv run --python 3.12 --extra dev python scripts/validate.py`: passed
- Decisions:
  - none
- Remaining:
  - PostgreSQL-specific active-session uniqueness and processed-update constraint coverage remains for D2.6/D2.7.

### 2026-06-21 - Task D2.4

- Status: DONE
- Changed files:
  - `src/tg_typist/db/models.py`
  - `src/tg_typist/db/repositories.py`
  - `tests/integration/test_repositories.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added an explicit active-session history query that returns saved user/assistant messages in deterministic chronological order and excludes closed sessions.
  - Added a repository reset operation that closes the current active session with `closed_at` and `reset_reason`, then creates and returns a fresh active session; it also creates a session when none is active.
  - Kept archived session messages in the database while proving they do not appear in the new active-session history after reset.
  - Added SQLite partial-index metadata for the active-session uniqueness index so local repository tests can represent multiple archived sessions plus one active session without claiming PostgreSQL concurrency coverage.
- Checks:
  - RED: `uv run --python 3.12 --extra dev pytest tests/integration/test_repositories.py::test_reset_archives_old_session_and_active_history_starts_empty -q`: failed as expected with `AttributeError: 'MessageRepository' object has no attribute 'list_active_session_history_for_user'`
  - `uv run --python 3.12 --extra dev pytest tests/integration/test_repositories.py::test_reset_archives_old_session_and_active_history_starts_empty -q`: passed, 1 test
  - `uv run --python 3.12 --extra dev pytest tests/integration/test_repositories.py -q`: passed, 6 tests
  - `uv run --python 3.12 --extra dev ruff check . --fix`: passed
  - `uv run --python 3.12 --extra dev ruff check .`: passed
  - `uv run --python 3.12 --extra dev mypy src tests`: passed
  - `uv run --python 3.12 --extra dev python scripts/validate.py`: passed
- Decisions:
  - none
- Remaining:
  - PostgreSQL-specific active-session uniqueness and processed-update constraint coverage remains for D2.6/D2.7.

### 2026-06-21 - Task D2.5

- Status: DONE
- Changed files:
  - `scripts/smoke_db.py`
  - `scripts/validate.py`
  - `tests/unit/test_smoke_db.py`
  - `tests/unit/test_validate_script.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added a safe-by-default DB smoke script that exits 0 with an explicit skip message when `DATABASE_URL` is not set.
  - When `DATABASE_URL` is set, the script runs Alembic migrations to `head`, then opens an async SQLAlchemy connection and verifies `SELECT 1`.
  - Added deterministic unit tests for skip behavior, migration/health orchestration, and database URL password redaction.
  - Added DB smoke to the validation gate; validation now uses the current Python executable for local Python subprocesses so `uv run` keeps dependency resolution consistent.
- Checks:
  - RED: `uv run --python 3.12 --extra dev pytest tests/unit/test_smoke_db.py -q`: failed as expected with `FileNotFoundError` for missing `scripts/smoke_db.py`.
  - RED: `uv run --python 3.12 --extra dev pytest tests/unit/test_validate_script.py::test_validation_steps_are_ordered_from_fast_to_broad -q`: failed as expected because `db-smoke` was not yet in validation steps.
  - `uv run --python 3.12 --extra dev pytest tests/unit/test_smoke_db.py tests/unit/test_validate_script.py -q`: passed, 5 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/smoke_db.py`: passed with `db smoke skipped: DATABASE_URL is not set`.
  - `uv run --python 3.12 --extra dev ruff check . --fix`: passed.
  - `uv run --python 3.12 --extra dev ruff check .`: passed.
  - `uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `uv run --python 3.12 --extra dev python -m compileall -q scripts`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
- Decisions:
  - none
- Remaining:
  - PostgreSQL-specific active-session uniqueness and processed-update constraint coverage remains for D2.6/D2.7.

### 2026-06-21 - Task D2.6

- Status: BLOCKED
- Changed files:
  - `tests/integration/test_postgres_constraints.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added an opt-in PostgreSQL integration test module gated by explicit `TEST_DATABASE_URL`; it intentionally does not fall back to `DATABASE_URL` to avoid destructive cleanup or migration writes against an application database.
  - The new tests run Alembic migrations to `head` against the provided PostgreSQL test database and prove the active-session partial unique index, closed+active session allowance, duplicate `processed_telegram_updates.update_id` rejection, and repository compatibility with reset/get-or-create/idempotency behavior.
  - Existing model and migration already encode `uq_interview_sessions_one_active_per_user` as a PostgreSQL partial unique index and processed-update uniqueness via primary/unique key.
  - No real PostgreSQL service was available in this environment: `TEST_DATABASE_URL`, `DATABASE_URL`, and `POSTGRES*` env vars were unset, and `psql`, `postgres`, and `docker` were not found on PATH.
- Checks:
  - `git status --short -- tests/integration/test_postgres_constraints.py src/tg_typist/db/migrations/versions/20260621_0001_create_core_tables.py plans/roadmap/tasks.md plans/roadmap/progress.md`: completed before changes; showed pre-existing dirty roadmap files and untracked migration file.
  - `env -u TEST_DATABASE_URL -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/integration/test_postgres_constraints.py -q`: passed with explicit skip, 5 skipped.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 40 passed and 5 skipped.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
  - Real PostgreSQL constraint tests: not run; blocked because no PostgreSQL URL/service is available.
- Decisions:
  - none
- Remaining:
  - Provide an isolated disposable `TEST_DATABASE_URL` and rerun `uv run --python 3.12 --extra dev pytest tests/integration/test_postgres_constraints.py -q`, or complete `D2.7` by adding a CI PostgreSQL service/Testcontainers flow that exercises these tests. Mark `D2.6` DONE only after real PostgreSQL tests pass.

### 2026-06-21 - Task D2.7

- Status: DONE
- Changed files:
  - `.github/workflows/ci.yml`
  - `tests/unit/test_ci_workflow.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added a separate `postgres-constraints` GitHub Actions job so the existing deterministic validation job remains fast and unchanged.
  - The new CI job provisions an ephemeral `postgres:16` service with a disposable test database/user/password, waits on `pg_isready`, and runs `tests/integration/test_postgres_constraints.py` with explicit `TEST_DATABASE_URL`.
  - Added deterministic local unit tests that inspect `.github/workflows/ci.yml` for the PostgreSQL service, health check, disposable DB settings, `TEST_DATABASE_URL`, and opt-in constraint-test command.
  - Left `D2.6` BLOCKED until the PostgreSQL constraint tests actually pass against a real PostgreSQL service in CI or via a local disposable `TEST_DATABASE_URL`.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_ci_workflow.py -q`: failed as expected because the workflow did not yet contain `postgres-constraints` or `TEST_DATABASE_URL`.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_ci_workflow.py -q`: passed, 2 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 42 passed and 5 skipped.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
  - Workflow secret scan for Telegram/DeepSeek key patterns in `.github/workflows/ci.yml`: passed, no matches.
  - CI run: not run locally; workflow added and locally inspected.
- Decisions:
  - none
- Remaining:
  - Watch the next GitHub Actions run; if `postgres-constraints` passes, rerun/review `D2.6` and mark it DONE.

### 2026-06-21 - Task T3.1

- Status: DONE
- Changed files:
  - `src/tg_typist/main.py`
  - `src/tg_typist/bot/__init__.py`
  - `src/tg_typist/bot/webhook.py`
  - `tests/unit/test_main.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added `create_app(settings: Settings | None = None) -> FastAPI` and an ASGI `app` entrypoint.
  - Added `GET /health` returning only non-secret status, service, version and environment metadata without Telegram, DeepSeek or database calls.
  - Added a `POST /telegram/webhook` router shell that accepts JSON updates and returns `202 {"status": "accepted"}` without dispatch, idempotency, database writes or external calls.
  - Added deterministic tests for health in test mode without credentials, health secret non-disclosure, and minimal webhook update acceptance.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_main.py -q`: failed as expected with `ModuleNotFoundError: No module named 'tg_typist.main'`.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_main.py -q`: passed, 3 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check . --fix`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check .`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 45 passed and 5 skipped.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
- Decisions:
  - none
- Remaining:
  - Continue with `T3.2` for Telegram webhook secret verification.

### 2026-06-21 - Task T3.2

- Status: DONE
- Changed files:
  - `src/tg_typist/bot/webhook.py`
  - `tests/unit/test_webhook.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added production-only verification for Telegram's `X-Telegram-Bot-Api-Secret-Token` webhook header.
  - Missing or wrong production secrets now return `403 {"detail": "Forbidden"}` without exposing the configured secret.
  - Kept non-production/test webhook behavior permissive so local tests do not require live Telegram secrets.
  - Used constant-time `secrets.compare_digest` for provided-vs-configured secret comparison and left dispatch, DB writes and idempotency for later tasks.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_webhook.py -q`: failed as expected because missing/wrong production secrets were accepted with 202.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_webhook.py -q`: passed, 4 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check . --fix`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check .`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 49 passed and 5 skipped.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
- Decisions:
  - none
- Remaining:
  - Continue with `T3.4`; `T3.3` remains blocked until `D2.6` has real PostgreSQL proof.

### 2026-06-21 - Task T3.4

- Status: DONE
- Changed files:
  - `src/tg_typist/bot/messages.py`
  - `src/tg_typist/bot/handlers.py`
  - `src/tg_typist/bot/router.py`
  - `tests/unit/test_bot_handlers.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added deterministic Russian UTF-8 texts for `/start`, `/help`, `/privacy` and `/reset`.
  - Added pure async command handlers that answer through a minimal message protocol without requiring a live Telegram bot token or network calls.
  - Added optional command-service hooks so `/start` can ensure an active session and `/reset` can reset it when DB/webhook wiring is introduced later.
  - Added an aiogram `command_router` registering exactly the four MVP command handlers.
  - Included privacy basics: saved messages for interview support, DeepSeek API processing, archived old sessions, `/reset`, deletion/export availability before broader release or via admin contact, and future retention-policy documentation.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py -q`: failed as expected with `ImportError: cannot import name 'messages' from 'tg_typist.bot'` before implementation.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py -q`: passed, 9 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check . --fix`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check .`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 58 passed and 5 skipped, 1 StarletteDeprecationWarning.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
- Decisions:
  - none
- Remaining:
  - DB persistence hooks are not wired to real repositories yet; webhook dispatch to aiogram and ordinary text-message handling remain for later tasks.
  - Continue with `T3.5`; `T3.3` remains blocked until `D2.6` has real PostgreSQL proof.

### 2026-06-21 - Task T3.5

- Status: DONE
- Changed files:
  - `src/tg_typist/bot/messages.py`
  - `src/tg_typist/bot/handlers.py`
  - `src/tg_typist/bot/router.py`
  - `src/tg_typist/db/repositories.py`
  - `src/tg_typist/service/__init__.py`
  - `src/tg_typist/service/interview.py`
  - `tests/unit/test_bot_handlers.py`
  - `tests/integration/test_text_message_shell.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added a deterministic Russian text placeholder confirming that inbound text was saved and DeepSeek will be connected later.
  - Added `handle_text_message` with an injectable text-service protocol; with an injected service it passes normalized Telegram user/chat/text IDs, and without one it only sends the placeholder.
  - Added an aiogram non-command text filter and registered the text handler after the command handlers so slash commands remain separate.
  - Added `InterviewService.save_text_message_shell` to upsert the Telegram user, get or create the active interview session, optionally record/mark the Telegram update, save the user message, and avoid any DeepSeek/model-call or assistant-message writes.
  - Allowed repository user-message saves when `telegram_update_id` is unavailable while preserving update-id idempotency when it is present.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py tests/integration/test_text_message_shell.py -q`: failed as expected with missing `handle_text_message` and `TEXT_PLACEHOLDER_MESSAGE` imports.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py tests/integration/test_text_message_shell.py -q`: passed, 14 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check . --fix`: passed after fixing line-length issues.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check .`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 63 passed and 5 skipped, 1 StarletteDeprecationWarning.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
- Decisions:
  - none
- Remaining:
  - Webhook JSON dispatch to aiogram, pre-dispatch idempotency and DeepSeek-backed interview processing remain for later tasks.
  - Continue with `T3.6`; `T3.3` remains blocked until `D2.6` has real PostgreSQL proof.

### 2026-06-21 - Task T3.6

- Status: DONE
- Changed files:
  - `src/tg_typist/bot/messages.py`
  - `src/tg_typist/bot/handlers.py`
  - `src/tg_typist/bot/router.py`
  - `tests/unit/test_bot_handlers.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added Russian UTF-8 responses for unsupported private messages and documented the private-chat-only MVP policy text.
  - Enforced the MVP group policy at handler level: private text still uses the text-service shell, while group/supergroup/channel commands, text and unsupported messages no-op without answers, persistence, or model calls.
  - Added a private unsupported-message handler that answers safely without DB, DeepSeek, or command/text service hooks.
  - Updated aiogram routing with private-only non-command text filtering and a private unsupported-message fallback registered after the text handler.
  - Added deterministic handler/router tests for unsupported private messages, group command/text no-op behavior, private text service preservation, slash-command exclusion, and private-only fallback filtering.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py -q`: failed as expected with `ImportError: cannot import name 'handle_unsupported_message'` before implementation.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py -q`: passed, 21 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check . --fix`: passed, 1 fix applied.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_bot_handlers.py tests/integration/test_text_message_shell.py -q`: passed, 23 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 72 passed and 5 skipped, 1 StarletteDeprecationWarning.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check .`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
  - Security grep for secret/key patterns across `src`, `tests` and `plans/roadmap`: no real secrets found; only expected config variable names and synthetic test placeholders matched.
- Decisions:
  - none
- Remaining:
  - Webhook JSON dispatch to aiogram, pre-dispatch idempotency and DeepSeek-backed interview processing remain for later tasks.
  - Continue with `L4.1`; `T3.3` remains blocked until `D2.6` has real PostgreSQL proof.

### 2026-06-22 - Task L4.1

- Status: DONE
- Changed files:
  - `src/tg_typist/llm/__init__.py`
  - `src/tg_typist/llm/prompts.py`
  - `src/tg_typist/prompts/__init__.py`
  - `src/tg_typist/prompts/typist_system.md`
  - `tests/unit/test_prompts.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added a deterministic bundled prompt loader using `importlib.resources`, returning a typed immutable `SystemPrompt` with stable version `typist_system_v1` and UTF-8 text.
  - Added a clear `PromptLoadError` path for missing/empty/unreadable prompt resources without exposing local filesystem paths or secrets.
  - Added the initial Russian MVP typist system-prompt placeholder markdown resource under package resources.
  - Added focused unit tests for non-empty versioned loading, Russian placeholder substrings, missing-resource errors and environment-secret independence.
- Checks:
  - RED: `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_prompts.py -q`: failed as expected with `ModuleNotFoundError: No module named 'tg_typist.llm'` before implementation.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit/test_prompts.py -q`: passed, 4 tests.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check . --fix`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev pytest tests/unit tests/integration -q`: passed, 76 passed and 5 skipped, 1 StarletteDeprecationWarning.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev ruff check .`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev mypy src tests`: passed.
  - `env -u DATABASE_URL ENVIRONMENT=test uv run --python 3.12 --extra dev python scripts/validate.py`: passed.
- Decisions:
  - none
- Remaining:
  - Continue with `L4.2` for the history builder; `T3.3` remains blocked until `D2.6` has real PostgreSQL proof.

### 2026-06-22 - Task T3.3

- Status: DONE
- Changed files:
  - `src/tg_typist/main.py`
  - `src/tg_typist/bot/webhook.py`
  - `tests/unit/test_webhook.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added DB session-factory wiring in the FastAPI app factory when `DATABASE_URL` is configured.
  - Added webhook-level Telegram update metadata extraction and `ProcessedTelegramUpdateRepository.record_received` before future dispatch side effects.
  - Added duplicate webhook handling that returns HTTP 202 with `{"status": "duplicate"}` without reprocessing the update.
  - Added a deterministic in-memory DB webhook test proving one `processed_telegram_updates` row is created and duplicate replay is skipped.
- Checks:
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\test_webhook.py`: passed, 5 tests and 1 StarletteDeprecationWarning.
  - `.\.venv\Scripts\ruff.exe check src\tg_typist\bot\webhook.py tests\unit\test_webhook.py src\tg_typist\main.py`: passed.
  - `.\.venv\Scripts\mypy.exe src tests\unit\test_webhook.py`: passed.
- Decisions:
  - none
- Remaining:
  - Concurrent retry hardening with atomic PostgreSQL insert or `IntegrityError` recovery remains a follow-up for the DB hardening/E2E replay tasks.
  - Future aiogram dispatch should mark failed updates with `mark_failed` if dispatch raises after the pre-dispatch record.

### 2026-06-22 - Task L4.2

- Status: DONE
- Changed files:
  - `src/tg_typist/llm/history.py`
  - `tests/integration/test_history.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
- Summary:
  - Added `HistoryBuilder` that loads the versioned system prompt and appends saved active-session user/assistant messages in repository order.
  - Added typed `LLMMessage` and `PromptHistory` records with prompt version, request message count and request char count for future model-call metadata.
  - Added integration tests for system-first empty history, archived-session exclusion after reset, latest saved user message inclusion and failed assistant-message exclusion.
- Checks:
  - `.\.venv\Scripts\python.exe -m pytest tests\integration\test_history.py`: passed, 4 tests.
  - `.\.venv\Scripts\ruff.exe check src\tg_typist\llm\history.py tests\integration\test_history.py`: passed.
  - `.\.venv\Scripts\mypy.exe src tests\integration\test_history.py`: passed.
- Decisions:
  - none
- Remaining:
  - Continue with `L4.3` for the DeepSeek HTTP client.

### 2026-06-22 - Task L4.3

- Status: DONE
- Changed files:
  - `.env.example`
  - `src/tg_typist/llm/deepseek.py`
  - `src/tg_typist/llm/errors.py`
  - `tests/unit/test_deepseek_client.py`
  - `plans/roadmap/tasks.md`
  - `plans/roadmap/progress.md`
  - `plans/roadmap/decisions.md`
- Summary:
  - Verified official DeepSeek docs for the OpenAI-compatible `/chat/completions` endpoint and current model IDs.
  - Added a typed async `DeepSeekClient` with `from_settings`, safe missing-key handling, default `deepseek-v4-flash`, env model override, timeout support and bounded retries for timeout/rate-limit/provider failures.
  - Added typed success/failure results carrying assistant text, token usage, finish reason, status/error metadata and latency without raw prompt or secrets.
  - Added mocked HTTP tests for payload/auth, default model, missing API key, timeout retry, retryable 503 recovery, non-retried auth failure with key redaction, invalid success shape and exhausted server errors.
  - Updated `.env.example` to use the verified default model.
- Checks:
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\test_deepseek_client.py`: passed, 8 tests.
  - `.\.venv\Scripts\ruff.exe check src\tg_typist\llm tests\unit\test_deepseek_client.py --fix`: passed, 2 fixes applied.
  - `.\.venv\Scripts\mypy.exe src tests\unit\test_deepseek_client.py`: passed.
- Decisions:
  - `DEC-010` verification update.
- Remaining:
  - Continue with `L4.4` for context-limit classification and explicit no-summarization retry fallback behavior.
