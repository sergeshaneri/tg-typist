"""Add model call fallback metadata.

Revision ID: 20260622_0002
Revises: 20260621_0001
Create Date: 2026-06-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260622_0002"
down_revision: str | None = "20260621_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add explicit fallback metadata to model call records."""

    op.add_column(
        "model_calls",
        sa.Column(
            "fallback_policy",
            sa.String(length=64),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "model_calls",
        sa.Column("fallback_reason", sa.String(length=128), nullable=True),
    )
    op.alter_column("model_calls", "fallback_policy", server_default=None)


def downgrade() -> None:
    """Remove model call fallback metadata."""

    op.drop_column("model_calls", "fallback_reason")
    op.drop_column("model_calls", "fallback_policy")
