# Architecture Plan

## Выбранный стек

Планируемый стек для MVP:

- Python 3.12+.
- FastAPI как HTTP-service для Railway, `/health` и Telegram webhook.
- aiogram 3 для Telegram Bot API handlers.
- SQLAlchemy 2 async ORM.
- Alembic migrations.
- asyncpg for PostgreSQL.
- httpx for DeepSeek API.
- pydantic-settings for environment config.
- pytest, pytest-asyncio, respx/httpx mocks for tests.
- ruff and mypy for static checks.

Точные версии зависимостей фиксируются в scaffold-задачах.

## Целевая структура

```text
src/
  tg_typist/
    __init__.py
    main.py                  # FastAPI app factory and production entrypoint
    settings.py              # env parsing and safe config representation
    logging.py               # structured logging and redaction
    bot/
      __init__.py
      router.py              # aiogram router registration
      handlers.py            # /start, /help, /privacy, /reset, text messages
      webhook.py             # Telegram webhook endpoint glue
      messages.py            # user-facing Russian texts
      rate_limit.py          # per-user limits
    db/
      __init__.py
      base.py
      models.py
      session.py
      repositories.py
      migrations/            # Alembic environment and versions
    llm/
      __init__.py
      deepseek.py            # HTTP adapter
      history.py             # active-session prompt assembly
      prompts.py             # prompt loading/versioning
      errors.py
    service/
      interview.py           # orchestration for one-message processing
      locks.py               # per-user async locks
      privacy.py             # deletion/export helpers later
    prompts/
      typist_system.md
scripts/
  validate.py
  smoke_config.py
  smoke_webhook.py
  smoke_db.py
tests/
  unit/
  integration/
  smoke/
```

## Runtime Flow

```text
Telegram webhook
  -> FastAPI endpoint
  -> webhook secret verification
  -> idempotency check for Telegram update_id
  -> aiogram dispatcher
  -> handler validates message and user
  -> InterviewService acquires per-user lock
  -> repository saves inbound message
  -> history builder loads active-session messages
  -> DeepSeek client sends system prompt + full history
  -> repository saves model call metadata
  -> repository saves assistant message
  -> Telegram sends assistant reply
```

## Layers

### HTTP Layer

Responsibilities:

- expose `/health`;
- receive Telegram webhook updates;
- verify webhook secret in production;
- reject or no-op duplicate Telegram `update_id` values before model calls;
- pass updates to aiogram dispatcher;
- avoid business logic in route functions.

Does not:

- build prompts;
- call DeepSeek directly;
- run database queries except health checks through a small service.

### Telegram Bot Layer

Responsibilities:

- parse commands;
- reject unsupported chat types or message types;
- send Russian user-facing responses;
- trigger `InterviewService` for text messages;
- show typing action while processing;
- convert internal errors into short user-facing messages.

Does not:

- assemble full prompt history;
- know SQL table details;
- hold DeepSeek API details.

### Interview Service Layer

Responsibilities:

- coordinate one incoming user message end to end;
- enforce per-user lock inside one process;
- use database idempotency and session constraints as the cross-process correctness layer;
- enforce rate limit and message length limit;
- save inbound message before model call;
- call history builder and DeepSeek adapter;
- save assistant response and model-call metadata;
- choose fallback behavior for context-limit errors.

This layer is the main integration seam for tests.

### LLM Layer

Responsibilities:

- load versioned system prompt;
- convert database messages to DeepSeek chat format;
- call DeepSeek with timeout and retry policy;
- parse success, token usage and errors;
- return typed results without exposing raw secrets.

The adapter should be OpenAI-compatible where possible, but the exact DeepSeek endpoint, model names and response fields must be verified against official DeepSeek docs during implementation. Do not default to deprecated model aliases. Prefer `deepseek-v4-flash` for cost/speed or `deepseek-v4-pro` for quality after checking current docs.

### Database Layer

Responsibilities:

- define schema and migrations;
- provide repository methods;
- hide SQLAlchemy details from handlers;
- support tests with transaction rollback or isolated database.
- enforce core invariants with PostgreSQL constraints where possible:
  - unique Telegram user ID;
  - partial unique index for one active session per user;
  - unique processed Telegram `update_id` or unique `(chat_id, message_id)` idempotency key;
  - foreign keys from messages and model calls to sessions/user messages.

### Configuration Layer

All runtime config comes from environment variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `PUBLIC_WEBHOOK_BASE_URL`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `DATABASE_URL`
- `PORT`
- `ENVIRONMENT`
- `LOG_LEVEL`
- `ADMIN_TELEGRAM_IDS`
- `MAX_MESSAGE_CHARS`
- `RATE_LIMIT_MESSAGES`
- `RATE_LIMIT_WINDOW_SECONDS`
- `DEEPSEEK_TIMEOUT_SECONDS`
- `DEEPSEEK_MAX_RETRIES`

`settings.py` must provide safe redacted output for logs and tests.

## History Assembly

MVP history builder:

1. Load active session.
2. Load all messages in chronological order.
3. Prepend the current system prompt.
4. Convert roles:
   - `user` -> Telegram user text;
   - `assistant` -> previous DeepSeek response;
   - system prompt is not stored as a normal chat message unless prompt versioning requires it.
5. Send the whole active-session history.

Context-limit fallback:

- Detect context-limit errors by typed error classification, not brittle raw text only.
- Record `history_policy=full` and `fallback_policy=tail_window` in `model_calls`.
- Retry once with the latest messages under a configured rough character budget.
- Inform the user that the conversation became too long and the bot will continue from the latest part.

No summarization in MVP unless the roadmap is updated.

## Testing Strategy

Test pyramid:

- Unit tests for settings, prompt loading, history assembly, rate limits, message length validation and error classification.
- Repository tests for users, sessions, messages and model calls.
- Service integration tests with mocked DeepSeek and fake Telegram sender.
- Webhook tests with FastAPI TestClient or AsyncClient.
- Migration and repository tests against real PostgreSQL in CI or an explicitly documented local test container/service. SQLite is not an adequate substitute for partial indexes, asyncpg behavior or PostgreSQL advisory locks.
- Optional live smoke tests gated by explicit environment variables.

Default tests must never call live Telegram or DeepSeek.

## Deployment Shape

Production service:

- Railway web service runs the FastAPI app.
- Railway Postgres provides `DATABASE_URL`.
- App binds to `0.0.0.0:$PORT`.
- Startup runs migrations or release command runs migrations before service start.
- After deploy, a script sets Telegram webhook to `PUBLIC_WEBHOOK_BASE_URL/telegram/webhook`.
- `/health` returns healthy when the app can start and optionally reach DB, but must not depend on DeepSeek.

Local development:

- `.env` file for local secrets, ignored by git.
- Local Postgres or Docker Compose can be added later.
- Polling mode may be added for local convenience, but production path remains webhook.

## Risks

- DeepSeek context limit can be hit if the full interview grows long. Mitigation: explicit fallback and later summarization/orchestrator.
- Telegram retries webhooks if response is slow. Mitigation: idempotency table, bounded handler timeout, and consider background processing if synchronous DeepSeek calls become unreliable.
- Railway cold starts can delay first reply. Mitigation: short timeouts and visible user error.
- Database migrations can drift from models. Mitigation: migration smoke test and repository tests.
- Prompt text can change without traceability. Mitigation: prompt versioning and model-call metadata.
- In-process user locks do not protect across multiple Railway replicas. Mitigation: MVP runs one replica, or use PostgreSQL advisory locks / DB-backed queue before scaling horizontally.
