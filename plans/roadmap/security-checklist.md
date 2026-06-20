# Security and Privacy Checklist

This checklist defines required safety checks for implementation tasks.

## Secrets

- `TELEGRAM_BOT_TOKEN` is read only from environment.
- `DEEPSEEK_API_KEY` is read only from environment.
- `DATABASE_URL` is read only from environment.
- `.env` is ignored by git.
- `.env.example` contains no real secrets.
- Logs redact tokens, keys and database passwords.
- Exceptions shown to users never include raw provider responses with secrets.

## Telegram

- Production webhook verifies `X-Telegram-Bot-Api-Secret-Token`.
- Telegram `update_id` idempotency is enforced before DeepSeek calls.
- MVP rejects or ignores group chats unless explicitly enabled.
- Unsupported message types get a safe response.
- Message length limit is enforced before database and DeepSeek pressure grows too high.
- Per-user rate limit is enforced.
- Per-user lock prevents concurrent prompt assembly races.

## DeepSeek

- HTTP timeout is configured.
- Retry policy is bounded.
- Context-limit error is classified and tested.
- Provider error is saved as metadata without full prompt.
- Full prompt payload is not logged.
- Tests use mocked HTTP by default.

## Database

- Migrations are required for schema changes.
- User table has unique Telegram ID.
- A user has at most one active session, enforced by PostgreSQL constraint.
- Processed Telegram updates are unique by `update_id` or an explicitly chosen idempotency key.
- Messages are linked to sessions.
- Model calls are linked to the user message that triggered them.
- `/reset` closes the current session without deleting old data.
- Deletion/export policy is planned before public release.

## Privacy Text

`/privacy` must state, in Russian:

- messages are saved to support the interview;
- messages are sent to DeepSeek API for AI response generation;
- old sessions may be stored as archive;
- user can reset the active interview with `/reset`;
- deletion/export process will be available before broader public release or through admin contact.
- retention policy will be documented before public release.

## Logging

Allowed by default:

- request IDs;
- Telegram user ID hashed or numeric if accepted by the user for private testing;
- session ID;
- message count;
- char count;
- model name;
- latency;
- status/error class.

Not allowed by default:

- full user message text;
- full assistant response text;
- full prompt payload;
- API tokens;
- Authorization headers;
- raw database URL with password.

## Release Gate

Before any public release:

- security checklist reviewed;
- privacy text reviewed;
- deletion/export procedure exists;
- retention policy exists;
- rate limiting tested;
- live smoke logs checked for redaction;
- admin IDs configured;
- Railway variables reviewed.
