# Domain Model

## Core Entities

### TelegramUser

Represents one Telegram account known to the bot.

Planned fields:

- `id`: internal UUID or bigint.
- `telegram_user_id`: Telegram numeric user ID, unique.
- `telegram_chat_id`: chat ID used for private conversation.
- `username`: optional, nullable.
- `first_name`: optional, nullable.
- `language_code`: optional, nullable.
- `is_blocked`: bool.
- `created_at`.
- `updated_at`.
- `last_seen_at`.

Privacy rule: store only fields useful for bot operation. Do not store profile photos or unnecessary Telegram metadata.

### InterviewSession

Represents one interview attempt.

Planned fields:

- `id`: UUID.
- `user_id`.
- `status`: `active`, `closed`, `errored`.
- `started_at`.
- `closed_at`.
- `reset_reason`: optional.
- `system_prompt_version`.
- `history_policy`: initially `full_active_session`.

Rules:

- A user must have at most one active session, enforced by a PostgreSQL partial unique index on active sessions.
- `/reset` closes the active session and creates a new one.
- Old sessions stay archived but are not included in MVP prompt history.

### ProcessedTelegramUpdate

Represents a Telegram update that has already been accepted for processing.

Planned fields:

- `update_id`: Telegram update ID, unique.
- `telegram_user_id`: nullable until parsed, useful for diagnostics.
- `telegram_chat_id`: nullable until parsed.
- `telegram_message_id`: nullable.
- `status`: `received`, `processed`, `failed`.
- `created_at`.
- `processed_at`: nullable.

Rules:

- Insert or check this record before calling DeepSeek.
- A duplicate `update_id` must not create another message or another model call.
- If an update was accepted but processing failed, retry behavior must be explicit: either resume safely from saved state or return no-op and rely on user retry.

### Message

Represents user and assistant messages.

Planned fields:

- `id`: UUID.
- `session_id`.
- `telegram_message_id`: nullable for assistant messages if not available at save time.
- `telegram_update_id`: nullable for assistant messages, required for user messages from Telegram.
- `role`: `user` or `assistant`.
- `text`: message content.
- `created_at`.
- `source`: `telegram`, `deepseek`, `system_notice`.
- `model_call_id`: nullable, set for assistant messages produced by a model call.
- `status`: `saved`, `sent`, `failed_to_send`.

Rules:

- Save inbound user message before calling DeepSeek.
- User messages from Telegram should have a unique idempotency guard through `ProcessedTelegramUpdate` or `(session_id, telegram_update_id)`.
- Only `user` and `assistant` messages are sent as chat history. The system prompt is prepended from prompt storage.
- Do not store raw full prompt payload separately unless a later task adds encrypted audit storage.

### ModelCall

Represents one DeepSeek request attempt.

Planned fields:

- `id`: UUID.
- `session_id`.
- `user_message_id`.
- `provider`: `deepseek`.
- `model`.
- `system_prompt_version`.
- `history_policy`: `full_active_session`, `tail_window_after_context_limit`.
- `request_message_count`.
- `request_char_count`.
- `status`: `success`, `timeout`, `rate_limited`, `context_limit`, `provider_error`, `unexpected_error`.
- `latency_ms`.
- `prompt_tokens`: nullable.
- `completion_tokens`: nullable.
- `total_tokens`: nullable.
- `error_code`: nullable.
- `error_message_redacted`: nullable.
- `created_at`.

Rules:

- Never store API key or Authorization header.
- Do not store full raw request/response by default.
- Store enough metadata to debug failures and context growth.

### SystemPrompt

MVP can use a file-backed prompt:

- `prompt_id`: `typist_system`.
- `version`: manually set string, for example date or semantic version.
- `path`: `src/tg_typist/prompts/typist_system.md`.
- `content`: loaded at runtime.

Later this can move to DB, but the first implementation should keep a stable file and record its version in `InterviewSession` and `ModelCall`.

### RateLimitBucket

Can be DB-backed or in-memory for MVP depending on task decision.

Planned fields if DB-backed:

- `telegram_user_id`.
- `window_started_at`.
- `message_count`.

Rule: tests must prove a user can send normal interview messages and gets blocked after configured excess.

## Message Roles

Internal roles:

- `user`: Telegram user's text.
- `assistant`: DeepSeek response sent by the bot.

Prompt roles sent to DeepSeek:

- `system`: current typist prompt.
- `user`: all active-session user messages in chronological order.
- `assistant`: all active-session assistant messages in chronological order.

## Session History Invariants

- Active-session history is ordered by `created_at`, then stable ID if needed.
- `/reset` never deletes old messages by default.
- `/reset` starts a new active session.
- History builder does not mix sessions.
- History builder does not include failed assistant messages.
- History builder includes the latest saved user message before calling DeepSeek.
- Duplicate Telegram updates do not change history after the first accepted processing attempt.

## Future Orchestrator Entities

Do not implement in MVP unless explicitly tasked, but keep schema evolution in mind:

### TypingHypothesis

- `session_id`.
- `target_kind`: `reinin_trait`, `model_a_function`, `type`, `quadra`.
- `target_id`.
- `hypothesis_text`.
- `confidence`.
- `evidence_message_ids`.
- `model_call_id`.

### PromptWindow

- `session_id`.
- `window_kind`: `global_typist`, `reinin_trait`, `model_a_function`.
- `window_id`.
- `system_prompt_version`.
- `last_updated_at`.
- `state_summary`.

### OrchestratorRun

- `session_id`.
- `incoming_message_id`.
- `selected_windows`.
- `aggregation_result`.
- `status`.

These entities should be introduced only after the single-prompt MVP works.
