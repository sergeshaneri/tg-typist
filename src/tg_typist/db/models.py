"""Core database models for Telegram interview sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tg_typist.db.base import Base

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_CLOSED = "closed"
SESSION_STATUS_ERRORED = "errored"
HISTORY_POLICY_FULL_ACTIVE_SESSION = "full_active_session"
HISTORY_POLICY_TAIL_WINDOW_AFTER_CONTEXT_LIMIT = "tail_window_after_context_limit"
FALLBACK_POLICY_NONE = "none"
FALLBACK_POLICY_TAIL_WINDOW = "tail_window"
FALLBACK_REASON_CONTEXT_LIMIT = "context_limit"
UPDATE_STATUS_RECEIVED = "received"
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_STATUS_SAVED = "saved"
MODEL_PROVIDER_DEEPSEEK = "deepseek"
MODEL_CALL_STATUS_PENDING = "pending"
MODEL_CALL_STATUS_SUCCESS = "success"
MODEL_CALL_STATUS_TIMEOUT = "timeout"
MODEL_CALL_STATUS_RATE_LIMITED = "rate_limited"
MODEL_CALL_STATUS_CONTEXT_LIMIT = "context_limit"
MODEL_CALL_STATUS_PROVIDER_ERROR = "provider_error"
MODEL_CALL_STATUS_UNEXPECTED_ERROR = "unexpected_error"


def utc_now() -> datetime:
    """Return an aware UTC timestamp for ORM defaults."""

    return datetime.now(UTC)


class UUIDPrimaryKeyMixin:
    """UUID primary key shared by core entities."""

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TimestampMixin:
    """Created/updated timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class TelegramUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Telegram account known to the bot."""

    __tablename__ = "telegram_users"
    __table_args__ = (UniqueConstraint("telegram_user_id"),)

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[InterviewSession]] = relationship(back_populates="user")


class InterviewSession(UUIDPrimaryKeyMixin, Base):
    """One interview attempt for one Telegram user."""

    __tablename__ = "interview_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=SESSION_STATUS_ACTIVE, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reset_reason: Mapped[str | None] = mapped_column(String(255))
    system_prompt_version: Mapped[str | None] = mapped_column(String(64))
    history_policy: Mapped[str] = mapped_column(
        String(64),
        default=HISTORY_POLICY_FULL_ACTIVE_SESSION,
        nullable=False,
    )

    user: Mapped[TelegramUser] = relationship(back_populates="sessions")
    messages: Mapped[list[Message]] = relationship(back_populates="session")
    model_calls: Mapped[list[ModelCall]] = relationship(back_populates="session")

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if self.status is None:
            self.status = SESSION_STATUS_ACTIVE
        if self.history_policy is None:
            self.history_policy = HISTORY_POLICY_FULL_ACTIVE_SESSION


Index(
    "uq_interview_sessions_one_active_per_user",
    InterviewSession.user_id,
    unique=True,
    postgresql_where=InterviewSession.status == SESSION_STATUS_ACTIVE,
    sqlite_where=InterviewSession.status == SESSION_STATUS_ACTIVE,
)


class ProcessedTelegramUpdate(Base):
    """Telegram update accepted for idempotent processing."""

    __tablename__ = "processed_telegram_updates"
    __table_args__ = (UniqueConstraint("update_id"),)

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default=UPDATE_STATUS_RECEIVED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list[Message]] = relationship(back_populates="telegram_update")


class Message(UUIDPrimaryKeyMixin, Base):
    """Stored user or assistant message."""

    __tablename__ = "messages"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id"), nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_update_id: Mapped[int | None] = mapped_column(
        ForeignKey("processed_telegram_updates.update_id"),
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    model_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_calls.id", use_alter=True, name="fk_messages_model_call_id_model_calls"),
    )
    status: Mapped[str] = mapped_column(String(32), default=MESSAGE_STATUS_SAVED, nullable=False)

    session: Mapped[InterviewSession] = relationship(back_populates="messages")
    telegram_update: Mapped[ProcessedTelegramUpdate | None] = relationship(
        back_populates="messages",
    )
    model_call: Mapped[ModelCall | None] = relationship(
        back_populates="assistant_messages",
        foreign_keys=[model_call_id],
    )


class ModelCall(UUIDPrimaryKeyMixin, Base):
    """Metadata for one DeepSeek request attempt."""

    __tablename__ = "model_calls"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id"), nullable=False)
    user_message_id: Mapped[UUID] = mapped_column(ForeignKey("messages.id"), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(32),
        default=MODEL_PROVIDER_DEEPSEEK,
        nullable=False,
    )
    model: Mapped[str | None] = mapped_column(String(128))
    system_prompt_version: Mapped[str | None] = mapped_column(String(64))
    history_policy: Mapped[str] = mapped_column(
        String(64),
        default=HISTORY_POLICY_FULL_ACTIVE_SESSION,
        nullable=False,
    )
    fallback_policy: Mapped[str] = mapped_column(
        String(64),
        default=FALLBACK_POLICY_NONE,
        nullable=False,
    )
    fallback_reason: Mapped[str | None] = mapped_column(String(128))
    request_message_count: Mapped[int | None]
    request_char_count: Mapped[int | None]
    status: Mapped[str] = mapped_column(
        String(32),
        default=MODEL_CALL_STATUS_PENDING,
        nullable=False,
    )
    latency_ms: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    total_tokens: Mapped[int | None]
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message_redacted: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[InterviewSession] = relationship(back_populates="model_calls")
    user_message: Mapped[Message] = relationship(foreign_keys=[user_message_id])
    assistant_messages: Mapped[list[Message]] = relationship(
        back_populates="model_call",
        foreign_keys=[Message.model_call_id],
    )

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        if self.provider is None:
            self.provider = MODEL_PROVIDER_DEEPSEEK
        if self.history_policy is None:
            self.history_policy = HISTORY_POLICY_FULL_ACTIVE_SESSION
        if self.fallback_policy is None:
            self.fallback_policy = FALLBACK_POLICY_NONE
        if self.status is None:
            self.status = MODEL_CALL_STATUS_PENDING
