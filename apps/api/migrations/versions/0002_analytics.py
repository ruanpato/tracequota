# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Read-only analytics views for provisioned Grafana."""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""CREATE VIEW request_usage AS
      SELECT e.id, e.task_id, e.timestamp::timestamptz AS time, t.provider, t.session_id, t.project,
      e.data->>'model' AS model, e.data->>'agent' AS agent, e.data->>'agent_type' AS agent_type,
      (e.data->>'demo')::boolean AS demo,
      (e.data->'tokens'->>'input')::bigint AS input,
      (e.data->'tokens'->>'output')::bigint AS output,
      (e.data->'tokens'->>'cache_read')::bigint AS cache_read,
      (e.data->'tokens'->>'cache_write')::bigint AS cache_write,
      (e.data->'pricing'->>'usd')::numeric AS estimated_api_cost
      FROM events e JOIN tasks t ON t.id=e.task_id WHERE e.kind='llm' """)
    op.execute("""CREATE VIEW quota_history AS
      SELECT q.id, q.provider, q.account, q.captured_at::timestamptz AS time,
      q.data->>'source' AS source, (q.data->>'demo')::boolean AS demo,
      w->>'name' AS window, (w->>'used_percent')::numeric AS used_percent,
      w->>'reset_at' AS reset_at
      FROM quota_snapshots q, LATERAL json_array_elements(q.data->'windows') w """)
    op.execute("""CREATE VIEW task_quota_deltas AS
      SELECT t.id, t.project, t.started_at::timestamptz AS time, (t.data->>'demo')::boolean AS demo,
      b.source AS source_before, a.source AS source_after, b.used_percent AS before_used, a.used_percent AS after_used,
      CASE WHEN b.reset_at IS DISTINCT FROM a.reset_at OR a.used_percent < b.used_percent
        OR (b.reset_at IS NOT NULL AND b.reset_at::timestamptz <= a.time AND b.reset_at::timestamptz > b.time)
        THEN NULL ELSE a.used_percent-b.used_percent END AS delta_pp
      FROM tasks t
      JOIN LATERAL (
        SELECT h.* FROM quota_history h JOIN quota_snapshots q ON q.id=h.id
        WHERE h.provider=t.provider AND h.account=COALESCE(t.data->>'account','default')
        AND h.demo=COALESCE((t.data->>'demo')::boolean,false) AND h.window='5h'
        AND (q.data->>'task_id' IS NULL OR q.data->>'task_id'=t.id)
        AND (q.data->>'session_id' IS NULL OR q.data->>'session_id'=t.session_id)
        AND h.time <= t.started_at::timestamptz AND h.time >= t.started_at::timestamptz-INTERVAL '24 hours'
        ORDER BY h.time DESC LIMIT 1) b ON true
      JOIN LATERAL (
        SELECT h.* FROM quota_history h JOIN quota_snapshots q ON q.id=h.id
        WHERE h.provider=t.provider AND h.account=COALESCE(t.data->>'account','default')
        AND h.demo=COALESCE((t.data->>'demo')::boolean,false) AND h.window='5h'
        AND (q.data->>'task_id' IS NULL OR q.data->>'task_id'=t.id)
        AND (q.data->>'session_id' IS NULL OR q.data->>'session_id'=t.session_id)
        AND h.time >= (t.data->>'completed_at')::timestamptz
        AND h.time <= (t.data->>'completed_at')::timestamptz+INTERVAL '15 minutes'
        ORDER BY h.time LIMIT 1) a ON true """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for view in ("task_quota_deltas", "quota_history", "request_usage"):
            op.execute("DROP VIEW " + view)
