"""Create core tables.

Revision ID: 20260621_0001
Revises:
Create Date: 2026-06-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create core MVP persistence tables."""

    op.create_table("telegram_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("telegram_user_id"),
    )

    op.create_table("interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_reason", sa.String(length=255), nullable=True),
        sa.Column("system_prompt_version", sa.String(length=64), nullable=True),
        sa.Column("history_policy", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"]),
    )
    op.create_index(
        "uq_interview_sessions_one_active_per_user",
        "interview_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table("processed_telegram_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("update_id"),
    )

    op.create_table("messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_update_id", sa.BigInteger(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("model_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.ForeignKeyConstraint(["telegram_update_id"], ["processed_telegram_updates.update_id"]),
    )

    op.create_table("model_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("system_prompt_version", sa.String(length=64), nullable=True),
        sa.Column("history_policy", sa.String(length=64), nullable=False),
        sa.Column("request_message_count", sa.Integer(), nullable=True),
        sa.Column("request_char_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message_redacted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"]),
    )
    op.create_foreign_key(
        "fk_messages_model_call_id_model_calls",
        "messages",
        "model_calls",
        ["model_call_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop core MVP persistence tables."""

    op.drop_constraint("fk_messages_model_call_id_model_calls", "messages", type_="foreignkey")
    op.drop_table("model_calls")
    op.drop_table("messages")
    op.drop_table("processed_telegram_updates")
    op.drop_index("uq_interview_sessions_one_active_per_user", table_name="interview_sessions")
    op.drop_table("interview_sessions")
    op.drop_table("telegram_users")
