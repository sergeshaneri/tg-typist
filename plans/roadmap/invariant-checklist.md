# Bot Invariant Test Checklist

This file is not a test. It is a checklist of required behavior that should become tests as implementation tasks add code.

## Settings

- Required env vars fail fast with clear errors in production mode.
- Optional env vars have documented defaults.
- Secret values are redacted in safe config output.
- Invalid numeric limits are rejected.
- `ENVIRONMENT=test` can run without live Telegram or DeepSeek keys.

## Users and Sessions

- Telegram user ID is unique.
- A new user gets exactly one active session.
- Existing user reuses active session.
- `/reset` closes old active session and creates a new one.
- Archived sessions are not included in active prompt history.
- A user cannot have two active sessions after repository operations complete.
- PostgreSQL partial unique index prevents two active sessions for the same user.

## Telegram Update Idempotency

- A new Telegram `update_id` is recorded before a DeepSeek call.
- Replaying the same `update_id` does not create a second user message.
- Replaying the same `update_id` does not create a second model call.
- Duplicate update handling is safe if the first processing attempt failed after saving the inbound message.
- Idempotency tests run against PostgreSQL, not SQLite-only substitutes.

## Messages

- User message is saved before DeepSeek call.
- Assistant message is saved only after successful model response.
- Failed DeepSeek call does not create successful assistant message.
- Message order is deterministic.
- Unsupported message types are handled without model call.
- Too-long messages are rejected before model call.

## History Builder

- System prompt is first in DeepSeek payload.
- All active-session user and assistant messages are included in chronological order.
- Archived sessions are excluded.
- Failed assistant sends are excluded unless a later decision changes this.
- Prompt version is recorded.
- Request message count and char count are recorded.

## DeepSeek Adapter

- Sends Authorization header only from env key.
- Applies timeout.
- Applies bounded retry policy.
- Parses successful response text.
- Parses token usage when present.
- Classifies timeout.
- Classifies provider error.
- Classifies context-limit error.
- Does not leak API key in exceptions or logs.

## Telegram Handlers

- `/start` creates or resumes active session.
- `/help` returns command list.
- `/privacy` returns required privacy text.
- `/reset` starts a new active session.
- Normal text triggers interview processing.
- Group chat behavior matches MVP policy.
- User-facing errors are short and do not expose internals.

## Rate Limit and Locks

- Rate limit allows normal use under configured threshold.
- Rate limit blocks excess messages.
- Per-user lock serializes two simultaneous messages from one user.
- Messages from different users can process concurrently.

## Database and Migrations

- Alembic migration creates all required tables.
- Models and migrations stay in sync.
- Repository tests can run on isolated test database or transaction.
- Migration smoke test can run in CI or be skipped with documented reason when Postgres is unavailable.

## Privacy and Logging

- Full prompt is not logged.
- Full user messages are not logged by default.
- Token and API key redaction works.
- Database URL redaction works.
- `/privacy` text mentions storage and DeepSeek.

## Deployment

- `/health` works without Telegram and DeepSeek calls.
- App binds to `0.0.0.0:$PORT` in production.
- Webhook endpoint rejects invalid secret in production.
- Webhook endpoint accepts valid secret.
- Webhook registration script does not print token.
- Railway env contract is documented.

## Future Orchestrator Readiness

- Messages have stable IDs.
- Model calls link to triggering message.
- Prompt version is recorded.
- Session boundary is explicit.
- Schema can add hypotheses without rewriting existing history.
