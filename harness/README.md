# Project Harness

This folder holds the repo-local AI harness: validation entrypoints, failure notes and workflow helpers.

Current harness:

- `AGENTS.md` is the root operating guide for future agents.
- `plans/roadmap/tasks.md` is the active task queue.
- `plans/roadmap/progress.md` tracks completed and blocked work.
- `plans/roadmap/decisions.md` records architecture, privacy, deployment and API decisions.
- `plans/roadmap/task-template.md` defines the required execution shape for atomic tasks.
- `plans/roadmap/handoff.md` contains prompts for clean-context task handoff.
- `plans/roadmap/security-checklist.md` defines safety and privacy checks for the bot.
- `harness/failure-log.md` records recurring agent failures and proposed harness fixes.

## Planned Validation Gate

Task `S1.4` must add `python scripts/validate.py` as the unified validation gate.

The gate should run, in order:

1. Python compile check.
2. Ruff lint.
3. Type check.
4. Unit tests.
5. Integration tests with mocked Telegram, DeepSeek and database where possible.
6. Config smoke test.
7. Webhook or polling smoke test.
8. Database migration smoke test.

Implementation agents should run focused checks first and the full validation gate before marking a task `DONE`.

## External Service Rule

Default tests must not call live Telegram or DeepSeek endpoints. Use mocks, fake adapters or recorded local fixtures that contain no real user messages or secrets.

Live smoke tests are allowed only when a task explicitly requests them and the user has supplied disposable credentials through environment variables. Live tests must be opt-in through a variable such as `RUN_LIVE_SMOKE=1`.

## Railway Rule

Railway-specific code should be thin:

- App config comes from environment variables.
- Database migrations are deterministic and can run before app start.
- `/health` must not depend on DeepSeek or Telegram availability.
- Webhook secret validation must be testable without Railway.
- The service must be able to start locally with the same code path as production, except for webhook URL registration.

## Database Rule

The application stores the full active-session conversation for the MVP. Schema changes must include migrations and repository tests.

For privacy:

- Avoid storing unnecessary Telegram profile fields.
- Keep old sessions archived rather than mixed into the active prompt.
- Add retention/deletion controls before any public release beyond private testing.

## Failure Handling Rule

If DeepSeek or Telegram fails:

- Save the inbound user message before attempting the model call.
- Record the failed request metadata without storing secrets.
- Reply with a short user-facing error if possible.
- Do not mark the assistant response as successfully generated.
- Tests must cover timeout, API error and context-limit paths.

## Harness Improvement Rule

Keep this harness practical. Add new checks when they catch real project risks.
