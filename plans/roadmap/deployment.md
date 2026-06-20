# Deployment Plan

## GitHub

Repository expectations:

- Source code and roadmap files are committed.
- Secrets are never committed.
- GitHub Actions runs deterministic checks on push and pull request.
- CI does not call live Telegram or DeepSeek.

Planned workflow:

```text
checkout
setup Python
install dependencies
run python scripts/validate.py
```

## Railway

Railway services:

- Web service: FastAPI Telegram webhook app.
- PostgreSQL plugin: stores users, sessions, messages and model calls.

Required variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `PUBLIC_WEBHOOK_BASE_URL`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `DATABASE_URL`
- `PORT`
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`
- `ADMIN_TELEGRAM_IDS`
- `MAX_MESSAGE_CHARS`
- `RATE_LIMIT_MESSAGES`
- `RATE_LIMIT_WINDOW_SECONDS`
- `DEEPSEEK_TIMEOUT_SECONDS`
- `DEEPSEEK_MAX_RETRIES`

Optional variables:

- `RUN_LIVE_SMOKE`
- `PRIVACY_CONTACT`
- `SENTRY_DSN` or another error-monitoring DSN if added later.

## Startup

Production startup should do one of these:

1. Run migrations as a release command, then start app.
2. Run migrations during startup with a lock, then start app.

Prefer release command if Railway setup makes it straightforward. Avoid running migrations from request handlers.

The web process must bind to `0.0.0.0:$PORT`. Railway injects `PORT`; local development can default to `8000`.

## Webhook Registration

Add a script or documented command that sets the Telegram webhook:

```text
https://api.telegram.org/bot<token>/setWebhook
  url=<PUBLIC_WEBHOOK_BASE_URL>/telegram/webhook
  secret_token=<TELEGRAM_WEBHOOK_SECRET>
```

The exact command must be implemented without printing the token.

## Health Checks

`GET /health` should return:

- service name;
- version or commit if available;
- environment;
- database status if lightweight;
- no secrets;
- no DeepSeek or Telegram dependency requirement.

## Smoke Tests

After deploy:

1. Open `/health`.
2. Verify migrations are applied.
3. Send `/start` to the bot.
4. Send a short test message.
5. Verify response arrives.
6. Verify database has user, session, messages and model call metadata.
7. Replay or simulate the same Telegram update and verify no duplicate message/model call is created.
8. Verify logs do not contain full prompt, API key or database URL.

Live smoke tests require disposable credentials or explicit user confirmation.
