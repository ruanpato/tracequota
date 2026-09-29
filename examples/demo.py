# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Deterministic daily synthetic workload. No provider account or LLM request."""

import os
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
from tracequota.domain import CATEGORIES, utc

API = os.getenv("API_URL", "http://localhost:8080")
OTLP = os.getenv("OTLP_URL", "http://localhost:4318")
DAY = os.getenv("DEMO_DATE", (datetime.now(timezone.utc) - timedelta(hours=12)).date().isoformat())


def attrs(data):
    def typed(v):
        return (
            {"boolValue": v}
            if isinstance(v, bool)
            else {"intValue": str(v)}
            if isinstance(v, int)
            else {"doubleValue": v}
            if isinstance(v, float)
            else {"stringValue": str(v)}
        )

    return [{"key": k, "value": typed(v)} for k, v in data.items()]


def ns(dt):
    return str(int(dt.timestamp() * 1e9))


def ident(value, size):
    return sha256(value.encode()).hexdigest()[:size]


def workload():
    start = datetime.fromisoformat(DAY + "T08:00:00+00:00")
    resources, metrics, quotas = [], [], []
    metric_totals = {}
    projects = ["tabledossier", "agent-workbench", "docs-engine"]
    titles = [
        "Add data quality checks",
        "Review export pipeline",
        "Improve search indexing",
        "Fix session persistence",
        "Write integration tests",
        "Refactor task correlation",
        "Add cache diagnostics",
        "Investigate timeout",
        "Update API documentation",
        "Build quota history",
    ]
    for i in range(20):
        task = f"demo-{DAY}-{i + 1:02}"
        session = f"demo-{DAY}-session-{i // 2 + 1:02}"
        project = projects[(i // 2) % 3]
        at = start + timedelta(minutes=i * 10)
        end = at + timedelta(seconds=180 + i * 12)
        trace = ident(task + "-trace", 32)
        root = ident(task + "-root", 16)
        sub = ident(task + "-sub", 16)
        common = {
            "service.name": "tracequota-demo",
            "tracequota.client.id": "claude_code",
            "tracequota.surface": "cli",
            "tracequota.runtime": "claude_code",
            "tracequota.integration_type": "native_otel",
            "tracequota.billing_platform": "anthropic",
            "tracequota.service_tier": "standard",
            "tracequota.region": "global",
            "tracequota.cache_write_ttl": "5m",
            "tracequota.usage.output_semantics": "inclusive_reasoning",
            "gen_ai.system": "anthropic",
            "session.id": session,
            "project.name": project,
            "tracequota.task.id": task,
            "tracequota.task.title": titles[i % 10],
            "tracequota.demo": True,
            "tracequota.source_surface": "synthetic-demo",
            "git.repository": f"https://example.invalid/demo/{project}",
            "git.branch": "feature/demo-usage",
            "git.commit": "a" * 40,
        }
        spans = [
            {
                "traceId": trace,
                "spanId": root,
                "name": "task",
                "startTimeUnixNano": ns(at),
                "endTimeUnixNano": ns(end),
                "attributes": attrs(
                    {
                        **common,
                        "tracequota.task.kind": "manual",
                        "openinference.span.kind": "CHAIN",
                        "tracequota.status": "failed" if i % 7 == 0 else "completed",
                    }
                ),
                "status": {"code": 2 if i % 7 == 0 else 1},
            },
            {
                "traceId": trace,
                "spanId": sub,
                "parentSpanId": root,
                "name": "Explore",
                "startTimeUnixNano": ns(at + timedelta(seconds=50)),
                "endTimeUnixNano": ns(end - timedelta(seconds=10)),
                "attributes": attrs(
                    {
                        **common,
                        "openinference.span.kind": "CHAIN",
                        "agent.name": "Explore",
                        "agent_id": sub,
                        "agent.type": "subagent",
                    }
                ),
            },
        ]
        total = dict.fromkeys(CATEGORIES, 0)
        for j in range(3):
            model = ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"][(i + (j == 2)) % 3]
            tokens = {
                "input": 4000 + i * 321 + j * 135,
                "output": 1100 + i * 121 + j * 72,
                "cache_read": 26000 + i * 1401 + j * 800,
                "cache_write": 2400 + i * 151,
            }
            total = {k: total[k] + tokens[k] for k in CATEGORIES}
            a = {
                **common,
                "openinference.span.kind": "LLM",
                "gen_ai.request.model": model,
                "gen_ai.response.id": f"{task}-request-{j}",
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "cache_read_tokens": tokens["cache_read"],
                "cache_creation_tokens": tokens["cache_write"],
                "agent.name": "main" if j < 2 else "Explore",
                "agent.type": "main" if j < 2 else "subagent",
            }
            if j == 2:
                a.update(agent_id=sub)
            spans.append(
                {
                    "traceId": trace,
                    "spanId": ident(task + f"-llm-{j}", 16),
                    "parentSpanId": root if j < 2 else sub,
                    "name": "LLM request",
                    "startTimeUnixNano": ns(at + timedelta(seconds=10 + j * 40)),
                    "endTimeUnixNano": ns(at + timedelta(seconds=30 + j * 40)),
                    "attributes": attrs(a),
                }
            )
        spans.append(
            {
                "traceId": trace,
                "spanId": ident(task + "-tool", 16),
                "parentSpanId": root,
                "name": "Read",
                "startTimeUnixNano": ns(at + timedelta(seconds=35)),
                "endTimeUnixNano": ns(at + timedelta(seconds=36)),
                "attributes": attrs({**common, "openinference.span.kind": "TOOL", "gen_ai.tool.name": "Read"}),
            }
        )
        resources.append(
            {
                "resource": {"attributes": attrs({"service.name": "tracequota-demo", "tracequota.demo": True})},
                "scopeSpans": [{"scope": {"name": "tracequota.synthetic"}, "spans": spans}],
            }
        )
        metric_totals.setdefault(project, dict.fromkeys(CATEGORIES, 0))
        for category, value in total.items():
            metric_totals[project][category] += value
        reset = utc(start + timedelta(hours=8))
        for side, dt, increment in [("before", at, 0), ("after", end, 3 + i % 7)]:
            quotas.append(
                {
                    "id": task + "-" + side,
                    "provider": "anthropic",
                    "account": "demo",
                    "captured_at": utc(dt),
                    "source": "manual",
                    "demo": True,
                    "session_id": session,
                    "task_id": task,
                    "windows": [
                        {"name": "5h", "type": "rolling", "used_percent": 20 + i * 2 + increment, "reset_at": reset},
                        {
                            "name": "weekly",
                            "type": "weekly",
                            "used_percent": 12 + i // 2 + bool(increment),
                            "reset_at": utc(start + timedelta(days=7)),
                        },
                    ],
                }
            )
        # Give tasks the same account as their quota evidence.
        for span in spans:
            span["attributes"] += attrs({"tracequota.account": "demo"})
    # Stable cumulative totals refresh the exporter on replay without adding deltas twice.
    # One stream per project/category also avoids conflicting same-label task counters.
    for project, total in metric_totals.items():
        metrics.append(
            {
                "resource": {"attributes": attrs({"service.name": "tracequota-demo", "tracequota.demo": True})},
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": "tracequota.demo.token_activity",
                                "unit": "{token}",
                                "sum": {
                                    "aggregationTemporality": 2,
                                    "isMonotonic": True,
                                    "dataPoints": [
                                        {
                                            "attributes": attrs(
                                                {
                                                    "project.name": project,
                                                    "model": "synthetic-mixed",
                                                    "type": k,
                                                    "tracequota.demo": True,
                                                }
                                            ),
                                            "startTimeUnixNano": ns(start),
                                            "timeUnixNano": ns(end),
                                            "asInt": str(v),
                                        }
                                        for k, v in total.items()
                                    ],
                                },
                            }
                        ]
                    }
                ],
            }
        )
    return resources, metrics, quotas


def run(client=None):
    client = client or httpx.Client(timeout=30)
    traces, metrics, quotas = workload()
    for snapshot in quotas:
        client.post(API + "/api/quota/snapshots", json=snapshot).raise_for_status()
    # One batch per task keeps retries bounded and demonstrates regular OTLP ingress.
    for resource in traces:
        client.post(OTLP + "/v1/traces", json={"resourceSpans": [resource]}).raise_for_status()
    for resource in metrics:
        client.post(OTLP + "/v1/metrics", json={"resourceMetrics": [resource]}).raise_for_status()
    from multi_client_demo import workload as multi_workload

    multi_traces, multi_quotas = multi_workload()
    for snapshot in multi_quotas:
        client.post(API + "/api/quota/snapshots", json=snapshot).raise_for_status()
    client.post(OTLP + "/v1/traces", json={"resourceSpans": multi_traces}).raise_for_status()
    print("Synthetic Claude fixture sent: 3 projects, 10 sessions, 20 tasks, 60 model calls, 40 quota snapshots.")
    print("Plus five multi-client tasks, including a two-provider OpenClaw task.")
    print("Replaying the same DEMO_DATE is idempotent. Traces and metrics pass through the Collector.")


if __name__ == "__main__":
    run()
