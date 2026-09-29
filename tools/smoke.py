# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Portable live stack assertions. Run inside Compose or on any host with Python."""

import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))
from demo import API, DAY, run
from smoke_helpers import eventually
from grafana_checks import check_grafana
from multi_client_checks import check_multi

PHOENIX = os.getenv("PHOENIX_URL", "http://localhost:6006")
PROM = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA = os.getenv("GRAFANA_URL", "http://localhost:3000")


with httpx.Client(timeout=20) as client:
    for url in (API + "/health", PHOENIX + "/healthz", PROM + "/-/healthy", GRAFANA + "/api/health"):
        client.get(url).raise_for_status()
    run(client)
    task_id = f"demo-{DAY}-01"

    def ledger():
        task = client.get(API + "/api/tasks/" + task_id).json()
        assert task["total_token_activity"] > 0 and task["llm_calls"] == 3
        assert all(task["tokens"][k] > 0 for k in ("input", "output", "cache_read", "cache_write"))
        assert task["main_agent_activity"] > 0 and task["subagent_activity"] > 0
        assert task["estimated_api_cost"] is not None and task["duration_seconds"] > 0
        assert task["quota_before"] and task["quota_after"] and task["quota_delta"][0]["delta_pp"] == 3
        return task

    task = eventually(ledger)
    check_multi(client, API, DAY)
    # Replay verifies durable deduplication, not merely successful HTTP acceptance.
    run(client)
    eventually(lambda: ledger())
    assert client.get(API + "/api/tasks/" + task_id).json()["total_token_activity"] == task["total_token_activity"]

    def phoenix():
        trace = task["phoenix_trace_ids"][0]
        result = client.post(
            PHOENIX + "/graphql",
            json={
                "query": "query($id: String!) { getTraceByOtelId(traceId: $id) { traceId } }",
                "variables": {"id": trace},
            },
        )
        result.raise_for_status()
        assert result.json().get("data", {}).get("getTraceByOtelId", {}).get("traceId") == trace, result.text

    eventually(phoenix)
    mixed = client.get(API + f"/api/tasks/multi-demo-{DAY}-03").json()
    mixed_trace = mixed["phoenix_trace_ids"][0]

    def mixed_phoenix():
        result = client.post(
            PHOENIX + "/graphql",
            json={
                "query": "query($id: String!) { getTraceByOtelId(traceId: $id) { traceId } }",
                "variables": {"id": mixed_trace},
            },
        )
        result.raise_for_status()
        assert result.json().get("data", {}).get("getTraceByOtelId", {}).get("traceId") == mixed_trace

    eventually(mixed_phoenix)

    def metric():
        result = client.get(
            PROM + "/api/v1/query", params={"query": 'tracequota_token_activity{demo="true",category="cache_read"}'}
        ).json()
        assert any(float(r["value"][1]) > 0 for r in result["data"]["result"])
        raw = client.get(
            PROM + "/api/v1/query", params={"query": '{__name__=~"tracequota_demo_token_activity.*"}'}
        ).json()
        assert raw["data"]["result"], "Collector synthetic metric missing"
        mixed_metrics = client.get(
            PROM + "/api/v1/query",
            params={
                "query": 'tracequota_client_token_activity{client="openclaw",provider="openai",category="cache_read"}'
            },
        ).json()
        assert any(float(r["value"][1]) > 0 for r in mixed_metrics["data"]["result"]), (
            "Mixed-client/provider series missing"
        )

    eventually(metric)
    datasources = client.get(
        GRAFANA + "/api/datasources", auth=("local", os.getenv("GRAFANA_PASSWORD", "tracequota-local"))
    )
    datasources.raise_for_status()
    assert {"prometheus", "tracequota-postgres"} <= {d["uid"] for d in datasources.json()}
    dashboard = client.get(GRAFANA + "/api/dashboards/uid/tracequota")
    dashboard.raise_for_status()
    assert len(dashboard.json()["dashboard"]["panels"]) >= 18
    check_grafana(client, GRAFANA, os.getenv("GRAFANA_PASSWORD", "tracequota-local"))
print("PASS: ledger, deduplication, quota, related Phoenix trace, Collector metrics, Grafana provisioning.")
print("Run tools/persistence.py after restarting the stack to verify stored task/quota records.")
