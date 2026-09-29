# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Initial metadata ledger."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("session_id", sa.String(160), nullable=False),
        sa.Column("project", sa.String(256), nullable=False),
        sa.Column("started_at", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("task_id", sa.String(160), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("timestamp", sa.String(40), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "quota_snapshots",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("account", sa.String(160), nullable=False),
        sa.Column("captured_at", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "metric_observations",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("timestamp", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_metric_observations_timestamp", "metric_observations", ["timestamp"])
    for table, fields in {
        "tasks": ["provider", "session_id", "project", "started_at"],
        "events": ["task_id", "timestamp", "kind"],
        "quota_snapshots": ["provider", "account", "captured_at"],
    }.items():
        for field in fields:
            op.create_index(f"ix_{table}_{field}", table, [field])


def downgrade():
    for table in ("events", "quota_snapshots", "tasks", "metric_observations"):
        op.drop_table(table)
