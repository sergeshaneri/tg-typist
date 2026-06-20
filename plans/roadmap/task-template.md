# Task Template

Every atomic task from `tasks.md` must be executable in a clean window without chat history. If a task needs more context, first expand this template or split the task.

## Copy/Paste Template

```md
# Task <ID>: <Title>

## Objective

One concrete result. Do not include adjacent improvements.

## Read First

- `AGENTS.md`
- `harness/README.md`
- `plans/roadmap/PRD.md`
- `plans/roadmap/domain-model.md`
- `plans/roadmap/architecture.md`
- `plans/roadmap/deployment.md`
- `plans/roadmap/security-checklist.md`
- `plans/roadmap/tasks.md`
- `plans/roadmap/progress.md`
- `plans/roadmap/decisions.md`
- `plans/roadmap/invariant-checklist.md`
- Relevant source files:
  - `<path>`

## Scope

In scope:

- `<file or behavior>`

Out of scope:

- `<explicit non-goal>`

## Likely Files

- `<path>`

## Constraints

- Keep the MVP single-prompt unless the task explicitly says orchestrator.
- Send full active-session history to DeepSeek unless the task explicitly changes policy.
- Do not store or print real Telegram tokens, DeepSeek keys or database credentials.
- Do not log full prompt payloads or full user messages by default.
- Keep Russian user-facing text and prompt text valid UTF-8.
- Add or update deterministic tests for behavior changes.
- Mock Telegram and DeepSeek by default.
- Do not call live APIs unless the task explicitly requires live smoke and credentials are provided.
- Keep changes surgical and avoid unrelated refactors.
- Work with existing dirty files; do not revert user changes.
- In Windows PowerShell, include the UTF-8 encoding prefix in the same command when printing repository files, diffs or other likely non-ASCII text.

## Steps

1. Run the drift check.
2. Inspect relevant source and tests.
3. Implement the smallest useful slice.
4. Add or update tests from `invariant-checklist.md` and `security-checklist.md`.
5. Run focused checks.
6. Run `python scripts/validate.py` if it exists.
7. Update `plans/roadmap/progress.md`.
8. Mark the task `DONE` in `plans/roadmap/tasks.md` only when objective and checks are complete.
9. Add a decision entry if architecture, privacy, API or deployment behavior changed.

## Drift Check

```powershell
git status --short -- <likely files>
```

If this is not a git repository yet, note that in progress and continue with file-level caution.

## Required Checks

- `python -m compileall -q src tests` after scaffold exists.
- `ruff check .` after ruff is installed.
- `mypy src tests` after mypy is configured.
- `pytest` after tests exist.
- `python scripts/validate.py` after S1.4 creates it.

For docs-only tasks, read back changed Markdown files and verify the task/progress state.

## Stop Conditions

Stop and report instead of improvising if:

- required API behavior is uncertain and would create incompatible code;
- required secrets are missing for an explicitly live task;
- a task requires changing privacy policy without user approval;
- a test exposes a real inconsistency outside this task's scope;
- the implementation would require a broad refactor not named in scope;
- validation fails for a reason unrelated to the task.

## Progress Ledger Update

Append this to `plans/roadmap/progress.md`:

```md
### YYYY-MM-DD - Task <ID>

- Status: DONE | BLOCKED
- Changed files:
  - `<path>`
- Summary:
  - `<what changed>`
- Checks:
  - `<command>`: passed | failed | not run, reason
- Decisions:
  - `DEC-000` or `none`
- Remaining:
  - `<follow-up or none>`
```
```

## Executor Rule

Do not mark a task `DONE` in `tasks.md` unless the task objective is complete, required checks were run or explicitly documented as impossible, and `progress.md` contains a ledger entry.
