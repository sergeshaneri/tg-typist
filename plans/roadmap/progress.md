# Roadmap Progress

## Snapshot

- Created: 2026-06-20.
- Current repository state: planning harness created before application scaffold.
- Current product target: Telegram bot on Railway with Railway PostgreSQL and DeepSeek API.
- MVP history policy: send full active-session conversation to DeepSeek.
- Validation: docs-only readback passed; code validation will be introduced by task `S1.4`.

## Current Status

| Area | Status | Notes |
|---|---:|---|
| Roadmap artifacts | DONE | PRD, architecture, domain model, deployment, security checklist, tasks and handoff created. |
| Application scaffold | BLOCKED | Scaffold files created; mandatory compile check is blocked because no working Python runtime is available in this environment. |
| Database | TODO | Railway PostgreSQL planned. |
| Telegram integration | TODO | Production webhook planned. |
| DeepSeek integration | TODO | Adapter planned with mocked tests. |
| Railway deployment | TODO | Deployment docs planned. |
| GitHub CI | TODO | Validation workflow planned after scaffold. |
| Future orchestrator | TODO | Out of MVP, but schema will preserve extension points. |

## Recommended Next Step

Unblock `S1.1` by installing or enabling Python 3.12+, then run `python -m compileall -q src` and mark the task `DONE` if it passes.

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

- Status: BLOCKED
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
  - `python -m compileall -q src`: failed, `python.exe` is the Windows Store alias and exits with `ResourceUnavailable: Указанный сеанс работы не существует. Возможно, он уже завершен.`
  - `py --version`: failed, `No installed Python found!`
  - `python3 --version`: failed, `python3.exe` is the Windows Store alias and exits with `ResourceUnavailable: Указанный сеанс работы не существует. Возможно, он уже завершен.`
- Decisions:
  - none
- Remaining:
  - Install or enable Python 3.12+, rerun `python -m compileall -q src`, then mark `S1.1` as `DONE` if the check passes.
