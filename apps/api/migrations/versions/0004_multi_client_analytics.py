# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Extend the existing request analytics view without removing its columns."""

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""CREATE OR REPLACE VIEW request_usage AS
      SELECT e.id, e.task_id, e.timestamp::timestamptz AS time, e.provider, t.session_id, t.project,
      e.data->>'model' AS model, e.data->>'agent' AS agent, e.data->>'agent_type' AS agent_type,
      (e.data->>'demo')::boolean AS demo,
      (e.data->'tokens'->>'input')::bigint AS input,
      (e.data->'tokens'->>'output')::bigint AS output,
      (e.data->'tokens'->>'cache_read')::bigint AS cache_read,
      (e.data->'tokens'->>'cache_write')::bigint AS cache_write,
      (e.data->'pricing'->>'usd')::numeric AS estimated_api_cost,
      e.client_id, COALESCE(e.data->>'surface','unknown') AS surface,
      COALESCE(e.data->>'runtime','unknown') AS runtime,
      COALESCE(e.data->>'integration_type','unknown') AS integration_type,
      COALESCE(e.data->>'billing_platform','unknown') AS billing_platform,
      t.data->>'repository' AS repository, e.pricing_rule_id,
      e.data->'pricing'->>'catalog_version' AS catalog_version,
      COALESCE(e.data->'pricing'->>'confidence',CASE WHEN e.data->'pricing'->>'usd' IS NOT NULL THEN 'legacy' ELSE 'unknown' END) AS pricing_confidence,
      COALESCE((e.data->'pricing'->>'partial_total')::numeric,(e.data->'pricing'->>'usd')::numeric) AS priced_partial_cost,
      (e.data->'usage'->>'input_total')::bigint AS measured_input_total,
      (e.data->'usage'->>'input_uncached')::bigint AS measured_input_uncached,
      (e.data->'usage'->>'cache_read')::bigint AS measured_cache_read,
      (e.data->'usage'->>'cache_write')::bigint AS measured_cache_write,
      (e.data->'usage'->>'output_total')::bigint AS measured_output_total,
      (e.data->'usage'->>'reasoning')::bigint AS measured_reasoning,
      e.data->'pricing'->'components' AS cost_components
      FROM events e JOIN tasks t ON t.id=e.task_id WHERE e.kind='llm' """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        # PostgreSQL cannot remove view columns through CREATE OR REPLACE.
        op.execute("DROP VIEW request_usage")
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
