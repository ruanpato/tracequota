# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Add execution identity and immutable catalogs; preserve all historical pricing payloads."""

import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.add_column("tasks", sa.Column("client_id", sa.String(80), nullable=False, server_default="unknown"))
    op.create_index("ix_tasks_client_id", "tasks", ["client_id"])
    for name, length, nullable in [
        ("client_id", 80, False),
        ("provider", 80, False),
        ("model_id", 160, False),
        ("pricing_rule_id", 200, True),
    ]:
        op.add_column(
            "events",
            sa.Column(name, sa.String(length), nullable=nullable, server_default=None if nullable else "unknown"),
        )
        op.create_index("ix_events_" + name, "events", [name])
    for name in ("raw_attributes", "normalized_attributes"):
        op.add_column("events", sa.Column(name, sa.JSON().with_variant(JSONB(), "postgresql"), nullable=True))
    op.create_table(
        "execution_sessions",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("client_id", sa.String(80), nullable=False),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    for field in ("client_id", "session_id"):
        op.create_index("ix_execution_sessions_" + field, "execution_sessions", [field])
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("task_id", sa.String(160), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("agent_id", sa.String(160), nullable=False),
        sa.Column("parent_agent_id", sa.String(160)),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    for field in ("task_id", "agent_id"):
        op.create_index("ix_agent_runs_" + field, "agent_runs", [field])
    op.create_table(
        "catalog_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("imported_at", sa.String(40), nullable=False),
        sa.Column("last_synced_at", sa.String(40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "pricing_rules",
        sa.Column("id", sa.String(300), primary_key=True),
        sa.Column("catalog_version", sa.String(64), sa.ForeignKey("catalog_versions.id"), nullable=False),
        sa.Column("rule_id", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("model_id", sa.String(160), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    for field in ("catalog_version", "rule_id", "provider", "model_id"):
        op.create_index("ix_pricing_rules_" + field, "pricing_rules", [field])
    # Only explicit source signals establish client identity; provider is never evidence.
    from tracequota.clients import identify

    bind = op.get_bind()
    tasks = sa.table("tasks", sa.column("id"), sa.column("data", sa.JSON()), sa.column("client_id"))
    events = sa.table(
        "events",
        sa.column("id"),
        sa.column("task_id"),
        sa.column("data", sa.JSON()),
        sa.column("client_id"),
        sa.column("provider"),
        sa.column("model_id"),
    )
    inferred = {}
    for row in bind.execute(sa.select(events.c.id, events.c.task_id, events.c.data)):
        data = json.loads(row.data) if isinstance(row.data, str) else row.data
        client = identify(data.get("attrs", {}))
        bind.execute(
            events.update()
            .where(events.c.id == row.id)
            .values(client_id=client, provider=data.get("provider", "unknown"), model_id=data.get("model", "unknown"))
        )
        if client != "unknown":
            inferred.setdefault(row.task_id, set()).add(client)
    for row in bind.execute(sa.select(tasks.c.id, tasks.c.data)):
        data = json.loads(row.data) if isinstance(row.data, str) else row.data
        clients = inferred.get(row.id, set())
        explicit = data.get("client_id")
        client = explicit or (next(iter(clients)) if len(clients) == 1 else "unknown")
        bind.execute(tasks.update().where(tasks.c.id == row.id).values(client_id=client))


def downgrade():
    for table in ("pricing_rules", "catalog_versions", "agent_runs", "execution_sessions"):
        op.drop_table(table)
    for name in ("raw_attributes", "normalized_attributes"):
        op.drop_column("events", name)
    for field in ("pricing_rule_id", "model_id", "provider", "client_id"):
        op.drop_index("ix_events_" + field, table_name="events")
        op.drop_column("events", field)
    op.drop_index("ix_tasks_client_id", table_name="tasks")
    op.drop_column("tasks", "client_id")
