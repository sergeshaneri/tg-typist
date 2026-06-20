# Telegram Typist Bot AI Guide

Use this file as the root operating guide for AI-assisted work in this repository.

## Project Map

- `plans/` contains the product plan, architecture, task queue, progress ledger and handoff prompts.
- `harness/` contains repo-local workflow rules, validation expectations and recurring failure notes.
- Future `src/tg_typist/` should contain the Python application package.
- Future `src/tg_typist/bot/` should contain Telegram update handlers and command routing.
- Future `src/tg_typist/llm/` should contain the DeepSeek client and prompt/history assembly.
- Future `src/tg_typist/db/` should contain database models, migrations and repositories.
- Future `src/tg_typist/prompts/` should contain versioned system prompts.
- Future `tests/` should contain unit, integration and smoke tests with Telegram and DeepSeek mocked by default.

## Working Rules

- Keep changes surgical. Do not refactor adjacent modules unless the active task requires it.
- Treat `plans/roadmap/PRD.md`, `plans/roadmap/architecture.md`, `plans/roadmap/domain-model.md`, `plans/roadmap/security-checklist.md` and `plans/roadmap/decisions.md` as the planning source of truth.
- Implement one atomic task from `plans/roadmap/tasks.md` at a time.
- Update `plans/roadmap/progress.md` after each completed or blocked task.
- Add a decision entry in `plans/roadmap/decisions.md` when making a choice that affects architecture, data shape, privacy, deployment or API behavior.
- Do not store Telegram tokens, DeepSeek keys, webhook secrets, database URLs or user messages in committed fixtures.
- Do not log full user messages by default. Logs may include message IDs, chat IDs hashed or redacted, durations, status codes and error classes.
- The MVP sends the full active-session conversation to DeepSeek. Do not silently replace this with summarization unless a task or user decision changes the policy.
- If a context-window error happens, degrade explicitly and record the behavior in tests and progress.
- Preserve Russian user-facing text and prompt text as UTF-8.
- On Windows PowerShell, include this UTF-8 prefix in any command that prints repository file contents, diffs or other likely non-ASCII text:
  `[Console]::InputEncoding = [Text.UTF8Encoding]::new(); [Console]::OutputEncoding = [Text.UTF8Encoding]::new(); $OutputEncoding = [Text.UTF8Encoding]::new(); <command>`.
- Prefer deterministic validation over subjective review.
- Work with existing dirty files. Do not revert user changes unless the user explicitly asks.

## Validation

The planned unified validation command is:

```powershell
python scripts/validate.py
```

That script does not exist yet. Task `S1.4` must create it after the Python scaffold exists.

Until then, docs-only work is validated by checking that the roadmap files exist and are readable. After scaffold tasks begin, every implementation task should run the smallest relevant checks first, then the unified validation command before marking the task done.

Planned focused checks:

- `python -m compileall -q src tests`
- `ruff check .`
- `mypy src tests`
- `pytest`
- `pytest tests/unit`
- `pytest tests/integration`
- `python scripts/smoke_config.py`
- `python scripts/smoke_webhook.py`
- `python scripts/smoke_db.py`

## Harness Improvement Rule

When an agent failure repeats or creates meaningful product, privacy, deployment or test risk, record it in `harness/failure-log.md` and propose one narrow improvement: a test, validation check, rule, workflow update or tool restriction.
