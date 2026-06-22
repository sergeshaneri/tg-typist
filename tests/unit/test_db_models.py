from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import cast

from sqlalchemy import Index, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from tg_typist.db.base import Base
from tg_typist.db.models import (
    FALLBACK_POLICY_NONE,
    HISTORY_POLICY_FULL_ACTIVE_SESSION,
    SESSION_STATUS_ACTIVE,
    InterviewSession,
    Message,
    ModelCall,
    ProcessedTelegramUpdate,
    TelegramUser,
)

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    ROOT / "src/tg_typist/db/migrations/versions/20260621_0001_create_core_tables.py"
)
FALLBACK_MIGRATION_PATH = (
    ROOT
    / "src/tg_typist/db/migrations/versions/20260622_0002_add_model_call_fallback_metadata.py"
)


def test_core_models_are_registered_in_metadata() -> None:
    assert set(Base.metadata.tables) >= {
        "telegram_users",
        "interview_sessions",
        "processed_telegram_updates",
        "messages",
        "model_calls",
    }

    assert TelegramUser.__tablename__ == "telegram_users"
    assert InterviewSession.__tablename__ == "interview_sessions"
    assert ProcessedTelegramUpdate.__tablename__ == "processed_telegram_updates"
    assert Message.__tablename__ == "messages"
    assert ModelCall.__tablename__ == "model_calls"


def test_user_and_update_tables_have_idempotency_constraints() -> None:
    user_table = cast(Table, TelegramUser.__table__)
    update_table = cast(Table, ProcessedTelegramUpdate.__table__)
    user_constraints = user_table.constraints
    update_constraints = update_table.constraints

    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"telegram_user_id"}
        for constraint in user_constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"update_id"}
        for constraint in update_constraints
    )


def test_active_session_partial_unique_index_targets_postgresql() -> None:
    session_table = cast(Table, InterviewSession.__table__)
    indexes = list(session_table.indexes)
    active_indexes = [
        index
        for index in indexes
        if isinstance(index, Index) and index.name == "uq_interview_sessions_one_active_per_user"
    ]

    assert len(active_indexes) == 1
    active_index = active_indexes[0]
    assert active_index.unique is True
    assert [column.name for column in active_index.columns] == ["user_id"]
    assert str(active_index.dialect_options["postgresql"]["where"]) == (
        "interview_sessions.status = :status_1"
    )


def test_foreign_keys_link_messages_and_model_calls() -> None:
    assert {fk.column.table.name for fk in InterviewSession.__table__.foreign_keys} == {
        "telegram_users"
    }
    assert {fk.column.table.name for fk in Message.__table__.foreign_keys} >= {
        "interview_sessions",
        "processed_telegram_updates",
        "model_calls",
    }
    assert {fk.column.table.name for fk in ModelCall.__table__.foreign_keys} >= {
        "interview_sessions",
        "messages",
    }


def test_model_defaults_match_mvp_policy() -> None:
    session = InterviewSession(user_id=TelegramUser().id)
    model_call = ModelCall(session_id=session.id, user_message_id=Message(session_id=session.id).id)

    assert session.status == SESSION_STATUS_ACTIVE
    assert session.history_policy == HISTORY_POLICY_FULL_ACTIVE_SESSION
    assert model_call.provider == "deepseek"
    assert model_call.history_policy == HISTORY_POLICY_FULL_ACTIVE_SESSION
    assert model_call.fallback_policy == FALLBACK_POLICY_NONE
    assert model_call.fallback_reason is None


def test_initial_migration_creates_core_tables_and_indexes() -> None:
    spec = importlib.util.spec_from_file_location("core_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20260621_0001"
    assert migration.down_revision is None

    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")
    for table_name in Base.metadata.tables:
        assert f'create_table("{table_name}"' in migration_text
    assert "uq_interview_sessions_one_active_per_user" in migration_text
    assert "postgresql_where" in migration_text


def test_metadata_compiles_for_postgresql() -> None:
    for table in Base.metadata.sorted_tables:
        str(CreateTable(table).compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]


def test_fallback_metadata_migration_adds_model_call_columns() -> None:
    spec = importlib.util.spec_from_file_location("fallback_migration", FALLBACK_MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20260622_0002"
    assert migration.down_revision == "20260621_0001"

    migration_text = FALLBACK_MIGRATION_PATH.read_text(encoding="utf-8")
    assert '"fallback_policy"' in migration_text
    assert '"fallback_reason"' in migration_text
    assert 'server_default="none"' in migration_text
