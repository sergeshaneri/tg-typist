# Decision Log

This file records product, domain, architecture, privacy and deployment decisions. New agents must read it before implementation tasks and append entries when making decisions that affect code shape or behavior.

## Entry Format

```md
## DEC-000: Short title

- Status: Proposed | Accepted | Superseded | Rejected
- Date: YYYY-MM-DD
- Owner: agent/user/name
- Related tasks: S1.1, M3.2

### Context

Why the decision is needed.

### Decision

What was decided.

### Consequences

What this simplifies, what risks it creates and what must be tested.
```

## DEC-001: Use Python async backend for MVP

- Status: Accepted
- Date: 2026-06-20
- Owner: planning
- Related tasks: S1.1, S1.2, S1.4

### Context

The bot needs Telegram integration, async API calls, PostgreSQL access, webhook serving and testable service boundaries.

### Decision

Use Python 3.12+, FastAPI, aiogram 3, SQLAlchemy async, Alembic, httpx, pytest, ruff and mypy for the first implementation.

### Consequences

The architecture is straightforward for async IO and tests. Agents should not introduce a second runtime such as Node.js unless the roadmap is updated.

## DEC-002: Production uses Telegram webhook on Railway

- Status: Accepted
- Date: 2026-06-20
- Owner: planning
- Related tasks: T3.1, T3.2, R7.1

### Context

Railway naturally hosts HTTP services, and webhook mode gives a clear `/health` endpoint and production request path.

### Decision

Production runs a FastAPI webhook service. Local development may add polling for convenience, but webhook remains the production path.

### Consequences

Implementation must verify Telegram webhook secret and provide a webhook registration script. Tests should cover the HTTP endpoint without live Telegram calls.

## DEC-003: MVP sends full active-session history to DeepSeek

- Status: Accepted
- Date: 2026-06-20
- Owner: user
- Related tasks: L4.1, L4.2, M5.1

### Context

The user prefers higher typing quality from full conversation context and wants to change concept only if limits become a real blocker.

### Decision

The first version sends the complete active-session message history to DeepSeek on each user message. It does not summarize by default and does not include archived sessions.

### Consequences

Context growth must be measured. Context-limit fallback must be explicit, tested and recorded in model-call metadata.

## DEC-004: Store conversation history in Railway PostgreSQL

- Status: Accepted
- Date: 2026-06-20
- Owner: planning
- Related tasks: D2.1, D2.2, R7.2

### Context

The bot needs durable history for full prompt assembly and later orchestrator work.

### Decision

Use Railway PostgreSQL for users, sessions, messages and model-call metadata.

### Consequences

Schema and migrations are part of MVP. Tests must prove `/reset` archives old history and keeps prompt assembly scoped to the active session.

## DEC-005: Tests mock Telegram and DeepSeek by default

- Status: Accepted
- Date: 2026-06-20
- Owner: planning
- Related tasks: S1.4, T3.3, L4.4, Q8.1

### Context

Future agents need deterministic tests that work without API keys, internet access or spending money.

### Decision

Default test suite must not call live Telegram or DeepSeek. Live smoke tests are opt-in through explicit environment variables and user-provided disposable credentials.

### Consequences

Adapter boundaries need fake implementations or HTTP mocks. The validation script should fail if live-test variables are absent only when live smoke mode is explicitly enabled.

## DEC-006: Telegram updates must be idempotent

- Status: Accepted
- Date: 2026-06-20
- Owner: planning review
- Related tasks: D2.2, D2.6, T3.3, M5.6, Q8.1

### Context

Telegram can retry webhook delivery when a request is slow or fails. The MVP may call DeepSeek during message processing, so duplicate delivery must not create duplicate messages or duplicate model calls.

### Decision

Store processed Telegram updates with a unique `update_id` or another explicit idempotency key before model calls. Duplicate updates must no-op or resume safely without invoking DeepSeek twice.

### Consequences

Database schema needs an idempotency table or constraint. Webhook integration tests must replay the same update and assert that message/model-call counts do not change.

## DEC-007: PostgreSQL enforces critical session invariants

- Status: Accepted
- Date: 2026-06-20
- Owner: planning review
- Related tasks: D2.2, D2.6, D2.7

### Context

Repository code can accidentally create two active sessions during concurrent `/start` or `/reset` operations. SQLite-like tests do not catch PostgreSQL partial-index behavior.

### Decision

Use PostgreSQL constraints for critical invariants, especially one active session per user and unique processed Telegram updates. Run migration/repository tests against real PostgreSQL in CI or an explicitly documented test service.

### Consequences

The project needs a Postgres-backed test path, not only pure unit tests. CI may be slightly slower, but it validates the behavior Railway will run.

## DEC-008: MVP runs one Railway replica unless DB locks are added

- Status: Accepted
- Date: 2026-06-20
- Owner: planning review
- Related tasks: M5.2, R7.1

### Context

An in-process async lock serializes messages only inside one running process. Multiple Railway replicas would allow concurrent processing for the same user unless a distributed lock or queue exists.

### Decision

MVP assumes one Railway replica. Before horizontal scaling, add PostgreSQL advisory locks, row-level locking or a DB-backed queue for per-user processing.

### Consequences

The plan can keep the simpler in-process lock for MVP, but deployment docs must not recommend horizontal scaling without the distributed-lock task.

## DEC-009: Railway runtime must bind the injected PORT

- Status: Accepted
- Date: 2026-06-20
- Owner: planning review
- Related tasks: S1.2, R7.1

### Context

Railway injects a `PORT` environment variable for web services. Ignoring it can make a successful local app fail in production.

### Decision

Production app startup must bind to `0.0.0.0:$PORT`, with a safe local fallback such as `8000`.

### Consequences

Settings and deployment smoke tests must verify the port contract.

## DEC-010: DeepSeek model defaults must follow current official docs

- Status: Accepted
- Date: 2026-06-20
- Owner: planning review
- Related tasks: L4.3

### Context

DeepSeek model names can change, and deprecated aliases should not become the project's default.

### Decision

Before implementing the adapter, verify official DeepSeek docs. Prefer `deepseek-v4-flash` for cost/speed or `deepseek-v4-pro` for quality if those names remain current. Do not hardcode deprecated aliases as defaults.

### Consequences

Model name stays configurable, and adapter tests should assert that configured model value is passed through.

### Verification Update - 2026-06-22

Official DeepSeek API docs were checked during `L4.3`. The OpenAI-compatible API uses `https://api.deepseek.com/chat/completions`; current documented model IDs are `deepseek-v4-flash` and `deepseek-v4-pro`; `deepseek-chat` and `deepseek-reasoner` are documented as deprecated on 2026-07-24 15:59 UTC. The MVP client default is `deepseek-v4-flash`, while `DEEPSEEK_MODEL` remains configurable.

## DEC-011: Model calls store fallback metadata, not prompt text

- Status: Accepted
- Date: 2026-06-22
- Owner: implementation
- Related tasks: L4.4, L4.5, M5.1

### Context

Context-limit fallback changes which prompt payload is sent to DeepSeek. The system needs enough metadata to debug that behavior without storing raw prompt/user text in `model_calls`.

### Decision

Add `fallback_policy` and `fallback_reason` to `model_calls`. Store request message count, character count, history policy, fallback policy/reason, status, latency, token usage and redacted error metadata. Do not store raw prompt messages or assistant response text in `model_calls`.

### Consequences

`M5.1` can persist model-call metadata before and after provider calls while preserving privacy. Prompt text remains in `messages`, scoped by session, and model-call rows only carry operational metadata.
