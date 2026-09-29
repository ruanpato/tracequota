# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import copy
from decimal import Decimal

from sqlalchemy import select

from examples import demo, multi_client_demo
from tracequota import db, pricing
from tracequota.clients import identify
from tracequota.telemetry import ALLOWED, normalise, sanitise_traces


def post_multi(client):
    resources, snapshots = multi_client_demo.workload()
    for snapshot in snapshots:
        assert client.post("/api/quota/snapshots", json=snapshot).status_code == 201
    assert client.post("/v1/traces", json={"resourceSpans": resources}).status_code == 200
    return resources


def test_client_is_not_provider_and_new_namespaces():
    assert identify({"gen_ai.provider.name": "anthropic", "input_tokens": 1}) == "unknown"
    assert identify({"tracequota.client.name": "OpenAI Codex"}) == "codex"
    assert identify({"service.name": "claude-code"}) == "claude_code"
    assert identify({}, "codex.api_request") == "codex"


def test_multi_provider_task_quotas_costs_and_filters(client):
    post_multi(client)
    rows = client.get("/api/tasks?demo=true&client=openclaw").json()
    assert len(rows) == 2
    mixed = client.get(f"/api/tasks/multi-demo-{demo.DAY}-03").json()
    assert mixed["providers"] == ["anthropic", "openai"]
    assert {q["provider"] for q in mixed["quota_by_provider"]} == {"anthropic", "openai"}
    assert all(q["delta"][0]["delta_pp"] == 3 for q in mixed["quota_by_provider"])
    calls = [e for e in mixed["events"] if e["kind"] == "llm"]
    assert Decimal(mixed["estimated_api_equivalent_cost"]) == sum(Decimal(e["pricing"]["total"]) for e in calls)
    scoped = client.get("/api/tasks?client=openclaw&provider=openai").json()
    assert len(scoped) == 1 and scoped[0]["llm_calls"] == 2
    scoped_total = sum(Decimal(e["pricing"]["total"]) for e in calls if e["provider"] == "openai")
    assert Decimal(scoped[0]["estimated_api_equivalent_cost"]) == scoped_total
    overview = client.get("/api/overview?client=openclaw&provider=openai").json()
    assert set(overview["costs"]["client_id"]) == {"openclaw"}
    assert set(overview["costs"]["provider"]) == {"openai"}
    assert Decimal(overview["estimated_api_equivalent_cost"]) == scoped_total
    for filters in [
        "model=gpt-6-sol",
        "client=codex",
        "provider=google",
        "surface=cli",
        "runtime=codex",
        "integration_type=tracequota_adapter",
        "billing_platform=google",
        "project=multi-client-workbench",
        "agent=Explore",
        "pricing_confidence=exact",
        "repository=https://example.invalid/demo/tabledossier",
    ]:
        assert client.get("/api/tasks?" + filters).json(), filters
    assert client.get("/api/tasks?client=codex&provider=anthropic").json() == []
    assert client.get("/api/sessions?client=openclaw&provider=openai").json()[0]["client_id"] == "openclaw"
    assert client.get("/api/projects?client=codex").json()[0]["estimated_api_equivalent_cost"] is not None


def test_catalog_sync_does_not_reprice_history(client, tmp_path):
    post_multi(client)
    ident = f"multi-demo-{demo.DAY}-02"
    original = client.get("/api/tasks/" + ident).json()
    catalogs, _ = pricing.load_registry()
    (tmp_path / "providers").mkdir()
    import json

    for catalog in catalogs:
        raw = catalog.model_dump(mode="json")
        for rule in raw["rules"]:
            rule["rates"][0]["rate"] = "999"
        (tmp_path / "providers" / (catalog.provider + ".json")).write_text(json.dumps(raw))
    with db.transaction() as session:
        result = pricing.sync(session, tmp_path)
    assert result["imported"]
    post_multi(client)
    replay = client.get("/api/tasks/" + ident).json()
    assert replay["estimated_api_equivalent_cost"] == original["estimated_api_equivalent_cost"]
    assert [e["pricing"] for e in replay["events"]] == [e["pricing"] for e in original["events"]]
    with db.Session() as session:
        assert len(session.scalars(select(db.CatalogVersion)).all()) == 2


def test_cross_client_request_collision_separate_and_idempotent(client):
    resources, _ = multi_client_demo.workload()
    first = copy.deepcopy(resources[1])
    second = copy.deepcopy(first)
    for span in second["scopeSpans"][0]["spans"]:
        for a in span["attributes"]:
            if a["key"] == "tracequota.client.id":
                a["value"] = {"stringValue": "openclaw"}
            if a["key"] == "tracequota.task.id":
                a["value"] = {"stringValue": "collision-other-client"}
    payload = {"resourceSpans": [first, second]}
    for _ in range(2):
        assert client.post("/v1/traces", json=payload).status_code == 200
    assert len(client.get("/api/tasks").json()) == 2
    assert all(t["llm_calls"] == 3 for t in client.get("/api/tasks").json())


def test_span_metadata_enrichment_preserves_identity_and_pricing(client):
    resources, _ = multi_client_demo.workload()
    resource = copy.deepcopy(resources[1])
    assert client.post("/v1/traces", json={"resourceSpans": [resource]}).status_code == 200
    with db.Session() as session:
        originals = {e.id: e.data.get("pricing") for e in session.scalars(select(db.Event))}
    for span in resource["scopeSpans"][0]["spans"]:
        span["attributes"] += demo.attrs({"tracequota.client.version": "new-version"})
    for _ in range(2):
        assert client.post("/v1/traces", json={"resourceSpans": [resource]}).status_code == 200
    with db.Session() as session:
        assert {e.id: e.data.get("pricing") for e in session.scalars(select(db.Event))} == originals


def test_raw_and_normalized_metadata_privacy_and_storage(client):
    resources, _ = multi_client_demo.workload()
    resources[1]["scopeSpans"][0]["spans"][2]["attributes"] += demo.attrs(
        {"prompt": "PRIVATE", "gen_ai.request.model": "requested-alias"}
    )
    payload = {"resourceSpans": [resources[1]]}
    records = normalise(payload, "traces")
    call = next(r for r in records if r["kind"] == "llm")
    assert call["model_requested"] == "requested-alias" and call["model_resolved"] == "gpt-6-sol"
    assert "PRIVATE" not in str(records) and "PRIVATE" not in str(sanitise_traces(payload))
    assert client.post("/v1/traces", json=payload).status_code == 200
    with db.Session() as session:
        event = session.scalar(select(db.Event).where(db.Event.kind == "llm"))
        assert event.raw_attributes["tracequota.client.id"] == "codex"
        assert event.normalized_attributes["model_resolved"] == "gpt-6-sol"
        assert "prompt" not in event.raw_attributes
    import yaml
    from pathlib import Path

    collector = yaml.safe_load(Path("infrastructure/otel/collector.yml").read_text())
    for signals in ("trace_statements", "log_statements", "metric_statements"):
        for group in collector["processors"]["transform/privacy"][signals]:
            for statement in group["statements"]:
                if statement.startswith("keep_keys") and statement != "keep_keys(attributes, [])":
                    import json

                    allowed = set(json.loads(statement[statement.index("[") : statement.rindex("]") + 1]))
                    assert allowed == ALLOWED


def test_date_filters_and_integrations_never_fake_live_connection(client):
    post_multi(client)
    assert client.get("/api/tasks?since=invalid").status_code == 422
    assert client.get("/api/tasks?since=2026-10-01&until=2026-09-01").status_code == 422
    assert client.get("/api/tasks?since=2099-01-01").json() == []
    integrations = client.get("/api/integrations").json()["clients"]
    assert next(c for c in integrations if c["id"] == "openclaw")["integration_type"] == "plugin_otel"
    assert all(c["last_seen"] is None for c in integrations)
    assert all(c["validation"] in ("untested", "planned", "synthetic_tested") for c in integrations)
    assert client.get("/api/filters").json()["client"] == ["claude_code", "codex", "gemini_cli", "openclaw"]
    metrics = client.get("/metrics").text
    assert 'client="openclaw",provider="openai"' in metrics
    assert 'client="openclaw",provider="anthropic"' in metrics


def test_legacy_request_identity_replay_preserves_price(client):
    resources, _ = multi_client_demo.workload()
    records = normalise({"resourceSpans": [resources[1]]}, "traces")
    call = next(r for r in records if r["kind"] == "llm")
    old_price = {"usd": "123.456", "version": "historical"}
    with db.transaction() as session:
        session.add(
            db.Task(
                id="legacy-task",
                provider="openai",
                session_id=call["session_id"],
                project="legacy",
                started_at=call["timestamp"],
                data={"status": "running", "demo": True, "trace_ids": [], "completed_at": None},
            )
        )
        session.flush()
        session.add(
            db.Event(
                id=call["legacy_id"],
                task_id="legacy-task",
                timestamp=call["timestamp"],
                kind="llm",
                data={**call, "id": call["legacy_id"], "pricing": old_price},
                provider="openai",
            )
        )
    for _ in range(2):
        from tracequota.main import ingest

        ingest([call])
    with db.Session() as session:
        assert len(session.scalars(select(db.Event)).all()) == 1
        event = session.get(db.Event, call["legacy_id"])
        assert event.data["pricing"] == old_price and event.client_id == "codex"


def test_aggregate_costs_are_not_truncated_by_task_list_limit(client):
    with db.transaction() as session:
        for i in range(1001):
            ident = f"large-{i}"
            session.add(
                db.Task(
                    id=ident,
                    provider="openai",
                    client_id="codex",
                    session_id="large-session",
                    project="large-project",
                    started_at="2026-09-28T08:00:00+00:00",
                    data={"status": "running", "demo": False, "trace_ids": [], "completed_at": None},
                )
            )
        session.flush()
        for i in range(1001):
            session.add(
                db.Event(
                    id=f"call-{i}",
                    task_id=f"large-{i}",
                    timestamp="2026-09-28T08:00:00+00:00",
                    kind="llm",
                    client_id="codex",
                    provider="openai",
                    model_id="test",
                    data={
                        "kind": "llm",
                        "client_id": "codex",
                        "provider": "openai",
                        "model": "test",
                        "agent": "main",
                        "agent_type": "main",
                        "tokens": {"input": 1, "output": 0, "cache_read": 0, "cache_write": 0},
                        "pricing": {"usd": "1"},
                        "provider_emitted_cost": None,
                        "timestamp": "2026-09-28T08:00:00+00:00",
                        "demo": False,
                    },
                )
            )
    assert len(client.get("/api/tasks?limit=1000").json()) == 1000
    overview = client.get("/api/overview?client=codex").json()
    assert Decimal(overview["estimated_api_equivalent_cost"]) == 1001
    assert overview["costs"]["client_id"]["codex"]["calls"] == 1001
    session = client.get("/api/sessions?client=codex").json()[0]
    assert session["tasks"] == 1001 and Decimal(session["estimated_api_equivalent_cost"]) == 1001
