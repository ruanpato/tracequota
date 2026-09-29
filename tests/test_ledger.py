# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

from decimal import Decimal
import importlib.util
from pathlib import Path

from google.protobuf.json_format import ParseDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from tracequota.domain import CATEGORIES, EstimatedQuotaProvider, estimate, quota_delta

spec = importlib.util.spec_from_file_location("demo", Path(__file__).parents[1] / "examples/demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
demo.DAY = "2026-09-28"


def batch(index=0):
    return {"resourceSpans": [demo.workload()[0][index]]}


def post_demo(client):
    traces, metrics, snapshots = demo.workload()
    for q in snapshots:
        assert client.post("/api/quota/snapshots", json=q).status_code == 201
    assert client.post("/v1/traces", json={"resourceSpans": traces}).status_code == 200
    assert client.post("/v1/metrics", json={"resourceMetrics": metrics}).status_code == 200


def test_end_to_end_synthetic_ledger(client):
    post_demo(client)
    tasks = client.get("/api/tasks?demo=true").json()
    assert len(tasks) == 20
    assert len(client.get("/api/sessions").json()) == 10
    assert len(client.get("/api/projects").json()) == 3
    task = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert task["tokens"] == {"input": 12405, "output": 3516, "cache_read": 80400, "cache_write": 7200}
    assert task["llm_calls"] == 3 and task["tool_calls"] == 1
    assert task["main_agent_activity"] > 0 and task["subagent_activity"] > 0
    assert task["estimated_api_cost"] is not None
    assert task["duration_seconds"] == 180
    assert task["quota_delta"][0]["delta_pp"] == 3
    assert task["quota_before"]["source"] == "manual"
    assert task["phoenix_trace_ids"]
    assert task["status"] == "failed"
    assert client.get("/api/tasks?demo=false").json() == []


def test_replayed_events_and_snapshots_are_idempotent(client):
    post_demo(client)
    original = client.get("/api/tasks/demo-2026-09-28-01").json()
    post_demo(client)
    replay = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert original["tokens"] == replay["tokens"]
    assert len(original["events"]) == len(replay["events"]) == 6
    assert len(client.get("/api/quota").json()) == 40


def test_protobuf_acceptance_and_trace_id_hex(client):
    request = ParseDict(batch(), ExportTraceServiceRequest())
    response = client.post(
        "/v1/traces", content=request.SerializeToString(), headers={"Content-Type": "application/x-protobuf"}
    )
    assert response.status_code == 200
    assert response.content == b""
    task = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert task["phoenix_trace_ids"][0] == demo.ident("demo-2026-09-28-01-trace", 32)


def test_log_and_span_request_deduplication(client):
    raw = batch()["resourceSpans"][0]["scopeSpans"][0]["spans"][2]
    logs = {
        "resourceLogs": [
            {
                "scopeLogs": [
                    {
                        "logRecords": [
                            {
                                "timeUnixNano": raw["startTimeUnixNano"],
                                "attributes": raw["attributes"] + demo.attrs({"event.name": "claude_code.api_request"}),
                                "body": {"stringValue": "claude_code.api_request"},
                            }
                        ]
                    }
                ]
            }
        ]
    }
    assert client.post("/v1/logs", json=logs).status_code == 200
    client.post("/v1/traces", json=batch())
    task = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert task["llm_calls"] == 3
    assert len([e for e in task["events"] if e["kind"] == "llm"]) == 3


def test_metadata_privacy_at_ledger_boundary(client):
    payload = batch()
    span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][2]
    span["attributes"] += demo.attrs(
        {"user_prompt": "SECRET_PROMPT", "tool_input": "SECRET_SOURCE", "api_key": "SECRET_KEY"}
    )
    span["events"] = [{"name": "SECRET_RESPONSE"}]
    client.post("/v1/traces", json=payload)
    assert "SECRET_" not in client.get("/api/tasks/demo-2026-09-28-01").text


def test_zero_tokens_missing_cost_unknown_model(client):
    payload = batch()
    for span in payload["resourceSpans"][0]["scopeSpans"][0]["spans"][2:5]:
        span["attributes"] = [
            a
            for a in span["attributes"]
            if a["key"]
            not in (
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_creation_tokens",
                "cost_usd",
                "gen_ai.request.model",
            )
        ]
        span["attributes"] += demo.attrs({"gen_ai.request.model": "unknown-model"})
    client.post("/v1/traces", json=payload)
    task = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert task["tokens"] == dict.fromkeys(CATEGORIES, 0)
    assert task["estimated_api_cost"] is None and task["observed_provider_cost"] is None
    assert task["unpriced_requests"] == 3
    assert task["quota_delta"] == []


def test_late_telemetry_does_not_reopen_completed_task(client):
    payload = batch()
    spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    late = spans.pop(4)
    client.post("/v1/traces", json=payload)
    before = client.get("/api/tasks/demo-2026-09-28-01").json()
    payload["resourceSpans"][0]["scopeSpans"][0]["spans"] = [late]
    client.post("/v1/traces", json=payload)
    after = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert after["llm_calls"] == before["llm_calls"] + 1
    assert after["completed_at"] == before["completed_at"]
    assert after["status"] == "failed"


def test_unnamed_subagent_and_no_git(client):
    payload = batch()
    spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    for span in spans:
        span["attributes"] = [
            a for a in span["attributes"] if a["key"] not in ("git.repository", "git.branch", "git.commit")
        ]
    spans[4]["attributes"] = [a for a in spans[4]["attributes"] if a["key"] not in ("agent.name", "agent_id")]
    client.post("/v1/traces", json=payload)
    task = client.get("/api/tasks/demo-2026-09-28-01").json()
    assert "unnamed subagent" in task["agents"]
    assert task["repository"] is None and task["git_branch"] is None


def test_official_statusline_drops_unrelated_content(client):
    r = client.post(
        "/api/quota/statusline",
        json={
            "session_id": "s1",
            "prompt": "SECRET",
            "rate_limits": {
                "five_hour": {"used_percentage": 37, "resets_at": 1790582400},
                "seven_day": {"used_percentage": 21},
            },
        },
    )
    assert r.status_code == 200
    q = client.get("/api/quota").json()[0]
    assert q["source"] == "official" and q["windows"][0]["remaining_percent"] == 63
    assert "SECRET" not in str(q)
    assert client.post("/api/quota/statusline", json={}).status_code == 422


def test_manual_task_lifecycle_and_identity_conflict(client):
    assert client.post("/api/tasks", json={"id": "manual", "session_id": "s"}).status_code == 201
    assert client.post("/api/tasks", json={"id": "manual"}).status_code == 409
    assert client.post("/api/tasks/manual/complete", json={}).status_code == 200
    assert client.get("/api/tasks/manual").json()["kind"] == "manual"
    assert client.get("/api/tasks/missing").status_code == 404


def test_source_labels_and_estimation_basis(client):
    assert client.post("/api/quota/estimate", json={"used_units": 20, "capacity": 80}).status_code == 201
    q = client.get("/api/quota").json()[0]
    assert q["source"] == "estimated" and q["windows"][0]["used_percent"] == 25
    assert q["estimation_basis"]["capacity"] == 80
    assert client.post("/api/quota/estimate", json={"used_units": 10, "capacity": 0}).status_code == 422


def test_api_filter_sort_and_metrics(client):
    post_demo(client)
    rows = client.get("/api/tasks?project=tabledossier&model=claude-sonnet-4-6&sort=total_token_activity").json()
    assert rows and all(t["project"] == "tabledossier" for t in rows)
    assert rows[0]["total_token_activity"] >= rows[-1]["total_token_activity"]
    assert client.get("/api/tasks?sort=invalid").status_code == 422
    assert 'tracequota_token_activity{category="cache_read",demo="true"}' in client.get("/metrics").text
    assert client.get("/health").json()["status"] == "healthy"


def test_untrusted_browser_origin_blocked(client):
    assert client.post("/api/tasks", json={}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/tasks", json={}, headers={"Origin": "http://localhost:8080"}).status_code == 201


def test_hook_discards_transcript_and_prompt(client):
    for name in ("SessionStart", "SessionEnd"):
        assert (
            client.post(
                "/api/hooks/claude",
                json={
                    "hook_event_name": name,
                    "session_id": "s1",
                    "prompt": "SECRET",
                    "transcript_path": "/SECRET/file",
                },
            ).json()
            == {}
        )
    rows = client.get("/api/tasks").json()
    assert rows[0]["kind"] == "session_activity" and rows[0]["status"] == "completed"
    assert "SECRET" not in str(rows)


def test_malformed_otlp_rejected(client):
    assert client.post("/v1/traces", content="bad", headers={"Content-Type": "application/json"}).status_code == 400
    assert client.post("/v1/unknown", json={}).status_code == 404


def test_quota_id_conflict_preserves_evidence(client):
    body = {"id": "same", "windows": [{"name": "5h", "used_percent": 10}], "captured_at": "2026-09-28T10:00:00Z"}
    assert client.post("/api/quota/snapshots", json=body).status_code == 201
    body["windows"][0]["used_percent"] = 20
    assert client.post("/api/quota/snapshots", json=body).status_code == 409


def test_quota_validation(client):
    assert (
        client.post("/api/quota/snapshots", json={"windows": [{"name": "5h", "used_percent": 101}]}).status_code == 422
    )
    assert (
        client.post(
            "/api/quota/snapshots",
            json={"windows": [{"name": "5h", "used_percent": 1}, {"name": "5h", "used_percent": 2}]},
        ).status_code
        == 422
    )


def snapshot(percent=30, reset="2026-09-28T12:00:00+00:00", time="2026-09-28T10:00:00+00:00"):
    return {
        "captured_at": time,
        "source": "manual",
        "windows": [{"name": "5h", "used_percent": percent, "reset_at": reset}],
    }


def test_quota_delta_in_percentage_points():
    assert quota_delta(snapshot(), snapshot(39, time="2026-09-28T11:00:00+00:00"))[0]["delta_pp"] == 9


def test_reset_at_boundary_and_negative_reset():
    for after in (
        snapshot(4, "2026-09-28T17:00:00+00:00", "2026-09-28T13:00:00+00:00"),
        snapshot(20),
        snapshot(60, time="2026-09-28T12:00:00+00:00"),
    ):
        result = quota_delta(snapshot(), after)[0]
        assert result["reset_crossed"] and result["delta_pp"] is None


def test_multiple_windows_and_missing_quota():
    before, after = snapshot(), snapshot(40)
    before["windows"].append({"name": "weekly", "used_percent": 11, "reset_at": None})
    after["windows"].append({"name": "weekly", "used_percent": 13, "reset_at": None})
    assert [w["delta_pp"] for w in quota_delta(before, after)] == [10, 2]
    assert quota_delta(None, after) == []


def test_versioned_pricing_and_cache_ttl():
    tokens = dict(zip(CATEGORIES, [1000000] * 4))
    assert Decimal(estimate("claude-sonnet-4-6", tokens, "2026-09-28")["usd"]) == Decimal("22.05")
    assert Decimal(
        estimate("claude-sonnet-4-6", tokens, "2026-09-28", {"tracequota.cache_write_ttl": "1h"})["usd"]
    ) == Decimal("24.3")
    assert estimate("unknown", tokens, "2026-09-28") is None
    assert estimate("claude-sonnet-4-6", tokens, "2026-09-27") is None
    assert estimate("claude-sonnet-4-6", tokens, "2026-09-28", {"speed": "fast"}) is None
    assert EstimatedQuotaProvider().snapshot(used_units=1, capacity=4).source == "estimated"


def test_phoenix_boundary_removes_scope_link_events_and_status_content(client, monkeypatch):
    from tracequota import main
    from tracequota.telemetry import sanitise_traces

    payload = batch()
    r = payload["resourceSpans"][0]
    r["schemaUrl"] = "SECRET_SCHEMA"
    r["scopeSpans"][0]["scope"] = {"name": "SECRET_SCOPE", "attributes": demo.attrs({"user_prompt": "SECRET"})}
    span = r["scopeSpans"][0]["spans"][0]
    span["name"] = "SECRET_NAME"
    span["events"] = [{"name": "SECRET_EVENT"}]
    span["status"] = {"code": 1, "message": "SECRET_MESSAGE"}
    span["links"] = [{"traceId": "a" * 32, "spanId": "a" * 16, "attributes": demo.attrs({"prompt": "SECRET_LINK"})}]
    captured = []

    async def forward(data):
        captured.append(sanitise_traces(data))

    monkeypatch.setattr(main, "forward_phoenix", forward)
    assert client.post("/phoenix/v1/traces", json=payload).status_code == 200
    assert "SECRET" not in str(captured)
    assert captured[0]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["links"][0]["traceId"] == "a" * 32


def test_demo_cumulative_metrics_match_ledger_without_counting_replays(client):
    post_demo(client)
    _, metrics, _ = demo.workload()
    sums = [metric["scopeMetrics"][0]["metrics"][0]["sum"] for metric in metrics]
    assert all(s["aggregationTemporality"] == 2 for s in sums)
    metric_total = sum(int(point["asInt"]) for s in sums for point in s["dataPoints"])
    rows = client.get("/api/tasks?demo=true").json()
    assert metric_total == sum(row["total_token_activity"] for row in rows)
    for _ in range(2):
        assert client.post("/v1/metrics", json={"resourceMetrics": metrics}).status_code == 200
    replay = client.get("/api/tasks?demo=true").json()
    assert sum(row["total_token_activity"] for row in replay) == metric_total
