# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).parents[1]


def test_additive_migration_preserves_events_ids_costs_and_safe_client_inference(tmp_path):
    url = "sqlite:///" + str(tmp_path / "preserved.db")
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(ROOT / "apps/api")}
    command = [sys.executable, "-m", "alembic", "-c", str(ROOT / "apps/api/alembic.ini"), "upgrade"]
    subprocess.run([*command, "0002"], env=env, check=True, capture_output=True)
    engine = create_engine(url)
    pricing_payload = {"usd": 1.23456789, "version": "old-catalog", "source": "historical"}
    events = [
        {
            "id": "claude-old",
            "provider": "anthropic",
            "model": "old-model",
            "pricing": pricing_payload,
            "attrs": {"event.name": "claude_code.api_request"},
        },
        {
            "id": "unknown-old",
            "provider": "anthropic",
            "model": "old-model",
            "pricing": pricing_payload,
            "attrs": {"input_tokens": 100},
        },
    ]
    with engine.begin() as connection:
        for event in events:
            connection.execute(
                text(
                    "INSERT INTO tasks (id, provider, session_id, project, started_at, data) VALUES (:id,'anthropic','session','project','2026-06-01T10:00:00+00:00',:data)"
                ),
                {
                    "id": event["id"],
                    "data": json.dumps({"source_surface": "claude-code", "title": "Preserve", "status": "running"}),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO events (id,task_id,timestamp,kind,data) VALUES (:id,:id,'2026-06-01T10:00:00+00:00','llm',:data)"
                ),
                {"id": event["id"], "data": json.dumps(event)},
            )
        connection.execute(
            text(
                "INSERT INTO quota_snapshots (id,provider,account,captured_at,data) VALUES ('quota','anthropic','default','2026-06-01',:data)"
            ),
            {"data": json.dumps({"source": "manual", "windows": []})},
        )
    subprocess.run([*command, "head"], env=env, check=True, capture_output=True)
    subprocess.run([*command, "head"], env=env, check=True, capture_output=True)
    with engine.connect() as connection:
        records = connection.execute(text("SELECT id,client_id,data FROM events ORDER BY id")).all()
        assert [r.id for r in records] == ["claude-old", "unknown-old"]
        assert [r.client_id for r in records] == ["claude_code", "unknown"]
        assert all(json.loads(r.data)["pricing"] == pricing_payload for r in records)
        assert connection.execute(text("SELECT count(*) FROM quota_snapshots")).scalar() == 1
        assert connection.execute(text("SELECT client_id FROM tasks WHERE id='unknown-old'")).scalar() == "unknown"
