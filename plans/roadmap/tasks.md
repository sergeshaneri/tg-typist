# Atomic Tasks

Statuses: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`.

## Execution Protocol

For any implementation task, a new agent must read `task-template.md`, check relevant items from `invariant-checklist.md` and `security-checklist.md`, record meaningful decisions in `decisions.md`, and finish by updating `progress.md`. If a task moves to a clean window, use `handoff.md`.

Do not implement more than one task at a time unless the user explicitly asks.

## Phase 0: Planning Harness

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| H0.1 | - | DONE | Create repo-local harness, PRD, architecture, decisions, checklists, handoff and task queue without application code. | `AGENTS.md`, `harness/*`, `plans/roadmap/*` | docs readback | Docs may overfit assumptions before code exists. |

## Phase 1: Python Scaffold and Validation Harness

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| S1.1 | H0.1 | DONE | Create Python project scaffold with package layout and dependency config. | `pyproject.toml`, `src/tg_typist/__init__.py`, `.gitignore`, `.env.example` | `python -m compileall -q src` | Wrong dependency versions or missing Railway-compatible start path. |
| S1.2 | S1.1 | DONE | Add settings module with env parsing, safe redaction, test defaults and Railway `PORT` handling. | `src/tg_typist/settings.py`, `tests/unit/test_settings.py` | `pytest tests/unit/test_settings.py` | Secrets could appear in repr/log output or app could ignore Railway port. |
| S1.3 | S1.2 | TODO | Add structured logging helper with redaction filters. | `src/tg_typist/logging.py`, `tests/unit/test_logging.py` | `pytest tests/unit/test_logging.py` | Logging full messages or secrets by accident. |
| S1.4 | S1.1 | TODO | Add unified validation script and baseline tooling. | `scripts/validate.py`, `scripts/smoke_config.py`, `pyproject.toml` | `python scripts/validate.py` | Validation may assume tests or DB before they exist; use staged checks. |
| S1.5 | S1.4 | TODO | Add GitHub Actions workflow for deterministic checks. | `.github/workflows/ci.yml` | local `python scripts/validate.py` | CI must not require live secrets. |

## Phase 2: Database Foundation

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| D2.1 | S1.2 | TODO | Add SQLAlchemy async engine/session setup and Alembic base. | `src/tg_typist/db/*`, `alembic.ini`, migrations env | `pytest tests/unit`, migration smoke if possible | Async DB config can diverge between local, CI and Railway. |
| D2.2 | D2.1 | TODO | Add models and migration for users, sessions, messages, processed Telegram updates and model calls. | `src/tg_typist/db/models.py`, migration version | repository model tests | Schema may miss future orchestrator extension points. |
| D2.3 | D2.2 | TODO | Add repositories for user/session/message/model-call operations. | `src/tg_typist/db/repositories.py`, `tests/integration/test_repositories.py` | repository tests | Multiple active sessions per user if uniqueness is weak. |
| D2.4 | D2.3 | TODO | Add active-session history query and reset transaction. | repository tests | `pytest tests/integration/test_repositories.py` | `/reset` could mix archived history into active prompt. |
| D2.5 | D2.2 | TODO | Add DB smoke script for migrations and health. | `scripts/smoke_db.py` | `python scripts/smoke_db.py` or documented skip | CI may lack Postgres; skip behavior must be explicit. |
| D2.6 | D2.2 | TODO | Enforce PostgreSQL constraints for one active session per user and unique processed Telegram updates. | migration version, repository tests | Postgres integration tests | SQLite cannot validate this; must use real PostgreSQL. |
| D2.7 | D2.6, S1.5 | TODO | Add CI PostgreSQL service or documented Testcontainers flow for DB constraints and migrations. | `.github/workflows/ci.yml`, test config | CI validation | Postgres service can slow CI if not scoped. |

## Phase 3: Telegram Webhook and Commands

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| T3.1 | S1.2 | TODO | Add FastAPI app factory with `/health` and Telegram webhook endpoint shell. | `src/tg_typist/main.py`, `src/tg_typist/bot/webhook.py`, tests | webhook tests | Health must not require live Telegram or DeepSeek. |
| T3.2 | T3.1 | TODO | Verify Telegram webhook secret in production and test accept/reject paths. | `bot/webhook.py`, tests | webhook secret tests | Rejecting local tests accidentally or accepting bad production requests. |
| T3.3 | D2.6, T3.1 | TODO | Add Telegram update idempotency before dispatching updates to handlers. | `bot/webhook.py`, repositories, tests | duplicate update webhook test | Telegram retries can duplicate messages/model calls. |
| T3.4 | D2.3, T3.1 | TODO | Add aiogram router and `/start`, `/help`, `/privacy`, `/reset` handlers. | `bot/router.py`, `bot/handlers.py`, `bot/messages.py`, tests | handler tests | User-facing text incomplete or not UTF-8. |
| T3.5 | T3.4 | TODO | Add text-message handler shell that saves inbound text and returns placeholder response without DeepSeek. | handlers, service skeleton, repository tests | integration test | Useful for testing DB/Telegram before LLM exists. |
| T3.6 | T3.4 | TODO | Add unsupported message and group-chat MVP policy handling. | handlers, messages, tests | handler tests | Bot may respond in groups when not intended. |

## Phase 4: DeepSeek Adapter and Prompt Handling

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| L4.1 | S1.2 | TODO | Add versioned system prompt loader and initial typist prompt file placeholder. | `src/tg_typist/llm/prompts.py`, `src/tg_typist/prompts/typist_system.md`, tests | prompt tests | Prompt may be too vague; user can replace content later. |
| L4.2 | D2.4, L4.1 | TODO | Add history builder that emits system prompt plus full active-session messages. | `src/tg_typist/llm/history.py`, tests | history tests | Accidentally sending archived sessions or missing latest user message. |
| L4.3 | S1.2 | TODO | Add DeepSeek HTTP client with typed success/error results, current model defaults, timeout and retries. | `src/tg_typist/llm/deepseek.py`, `llm/errors.py`, tests with respx | adapter tests | Exact DeepSeek response shape and model names need official-doc verification. |
| L4.4 | L4.3 | TODO | Add context-limit classification and one retry fallback contract without summarization. | `llm/errors.py`, `llm/history.py`, tests | context-limit tests | Fallback could silently violate full-history policy if not recorded. |
| L4.5 | L4.3 | TODO | Add model-call metadata persistence integration. | repositories, service tests | service tests | Error metadata could leak raw provider response. |

## Phase 5: Interview Service Integration

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| M5.1 | T3.5, L4.2, L4.3 | TODO | Implement `InterviewService.process_text_message` end to end with mocked DeepSeek. | `src/tg_typist/service/interview.py`, tests | service integration tests | Ordering bugs can produce incomplete prompt history. |
| M5.2 | M5.1 | TODO | Add per-user async lock and prove same-user serialization. | `service/locks.py`, tests | concurrency tests | Locks can leak memory or block all users globally. |
| M5.3 | M5.1 | TODO | Add message length limit and user-facing rejection. | service, handlers, tests | validation tests | Long messages can pressure DB/model if checked too late. |
| M5.4 | M5.1 | TODO | Add per-user rate limit. | `bot/rate_limit.py` or service module, tests | rate-limit tests | In-memory limits reset on deploy; acceptable for MVP if documented. |
| M5.5 | M5.1 | TODO | Replace placeholder text handler with full interview processing and Telegram typing action. | handlers, service tests | webhook/handler integration tests | Telegram retries can duplicate work if handler is slow. |
| M5.6 | M5.5, T3.3 | TODO | Add duplicate webhook E2E proving replayed update does not call DeepSeek twice. | integration tests | duplicate replay test | Idempotency must hold even when first processing failed mid-flow. |

## Phase 6: Privacy, Admin and Operational Safety

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| P6.1 | T3.4 | TODO | Finalize `/privacy` text according to security checklist. | `bot/messages.py`, tests | text test | Privacy statement may under-disclose DeepSeek processing. |
| P6.2 | S1.3, M5.1 | TODO | Add tests proving logs redact secrets and avoid full prompt/user messages. | logging, service tests | redaction tests | Test fixtures may accidentally include real data. |
| P6.3 | D2.3 | TODO | Add admin allowlist parsing and admin-only `/status`. | settings, handlers, tests | admin tests | Admin IDs can be misparsed or commands exposed. |
| P6.4 | D2.3 | TODO | Add admin procedure or command for deleting a user's stored data before external testing. | repositories, handlers or docs, tests | deletion tests | Data deletion needs careful cascading. |
| P6.5 | P6.4 | TODO | Add documented retention policy for archived sessions and model-call metadata. | `README.md`, `plans/roadmap/security-checklist.md`, tests if text exposed | docs readback | Retention policy needs user approval before public launch. |

## Phase 7: Railway and GitHub Deployment

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| R7.1 | T3.1, D2.5 | TODO | Add Railway start command/config and production app entrypoint binding `0.0.0.0:$PORT`. | `railway.toml` or docs, `Procfile` if needed | local start smoke | Railway runtime may differ from local. |
| R7.2 | D2.7 | TODO | Document Railway PostgreSQL setup and migration command. | `README.md`, `plans/roadmap/deployment.md` | docs review | Migrations can be skipped during deploy. |
| R7.3 | T3.2 | TODO | Add safe webhook registration script. | `scripts/set_webhook.py`, tests for token redaction | script dry-run test | Script might print token or hit live Telegram by default. |
| R7.4 | M5.5, R7.1, R7.3 | TODO | Run controlled live smoke with user-provided disposable credentials. | progress entry | live smoke checklist | Requires real secrets and Telegram bot; must be explicit. |

## Phase 8: End-to-End Test Hardening

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| Q8.1 | M5.6 | TODO | Add full mocked webhook E2E: `/start`, message, DeepSeek response, duplicate replay, `/reset`, second message. | `tests/integration/test_webhook_flow.py` | pytest integration | Hard to keep fake Telegram update payload realistic. |
| Q8.2 | M5.5 | TODO | Add failure E2E for DeepSeek timeout/provider error/context limit. | integration tests | pytest integration | User-facing error can diverge from service metadata. |
| Q8.3 | S1.4, Q8.1, Q8.2 | TODO | Ensure `python scripts/validate.py` runs all deterministic checks. | `scripts/validate.py` | validation gate | Full validation may be too slow or require unavailable Postgres. |
| Q8.4 | Q8.3 | TODO | Update README with local setup, tests, Railway deploy and smoke checklist. | `README.md` | docs readback | Docs can drift from actual commands. |

## Phase 9: Future Orchestrator Preparation

| ID | Depends | Status | Goal | Likely files | Checks | Risks |
|---|---|---:|---|---|---|---|
| O9.1 | M5.1 | TODO | Add design note for multi-window orchestrator without implementing it. | `plans/roadmap/architecture.md`, `domain-model.md` | docs readback | Premature complexity can distract from MVP. |
| O9.2 | D2.2 | TODO | Add migration plan for hypotheses/prompt windows as future-only tables or comments. | docs only or migration later | docs readback | Adding unused tables too early can increase maintenance. |
| O9.3 | Q8.3 | TODO | Create post-MVP task queue for Reinin-trait and Model-A prompt windows. | `plans/roadmap/tasks.md` | docs review | Needs user method text before implementation. |
