# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Partial native acceptance for development; full Compose acceptance is separate."""

import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parents[1] / "examples"))
from demo import API, DAY, run


def check():
    with httpx.Client(timeout=30) as client:
        run(client)
        task_id = f"demo-{DAY}-01"
        # Wait for the Collector batch and Phoenix's asynchronous persistence.
        from smoke_helpers import eventually

        def ledger():
            tasks = client.get(API + "/api/tasks?demo=true&limit=1000").json()
            assert len([t for t in tasks if t["id"].startswith(f"demo-{DAY}-")]) == 20
            task = client.get(API + "/api/tasks/" + task_id).json()
            assert task["llm_calls"] == 3 and task["tool_calls"] == 1
            assert all(task["tokens"][key] > 0 for key in ("input", "output", "cache_read", "cache_write"))
            assert task["main_agent_activity"] > 0 and task["subagent_activity"] > 0
            assert task["quota_delta"][0]["delta_pp"] == 3
            return task, tasks

        task, tasks = eventually(ledger)
        phoenix_url = os.getenv("PHOENIX_URL", "http://127.0.0.1:6006")
        trace = task["phoenix_trace_ids"][0]

        def phoenix():
            response = client.post(
                phoenix_url + "/graphql",
                json={
                    "query": "query($id: String!) { getTraceByOtelId(traceId: $id) { traceId } }",
                    "variables": {"id": trace},
                },
            )
            response.raise_for_status()
            assert response.json().get("data", {}).get("getTraceByOtelId", {}).get("traceId") == trace

        eventually(phoenix)
        metrics = client.get(os.getenv("COLLECTOR_METRICS_URL", "http://127.0.0.1:8889") + "/metrics")
        metrics.raise_for_status()
        assert "tracequota_demo_token_activity" in metrics.text
        ledger_metrics = client.get(API + "/metrics").text
        assert 'category="cache_read"' in ledger_metrics
        result = {
            "validation": "native partial acceptance; Docker/Prometheus/Grafana runtime not covered",
            "demo_date": DAY,
            "tasks": len(tasks),
            "llm_requests": sum(t["llm_calls"] for t in tasks),
            "token_activity": sum(t["total_token_activity"] for t in tasks),
            "example_task": task_id,
            "example_5h_delta_pp": task["quota_delta"][0]["delta_pp"],
            "phoenix_trace_id": trace,
            "collector_metrics_present": True,
        }
        output = Path(__file__).parents[1] / "docs" / "validation" / "native-smoke.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    check()
