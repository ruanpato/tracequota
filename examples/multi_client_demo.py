# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Additional synthetic clients, including one task with two inference providers."""

from copy import deepcopy

try:
    from examples import demo
except ModuleNotFoundError:
    import demo

FLOWS = [
    ("claude_code", "anthropic", "claude-sonnet-5-5"),
    ("codex", "openai", "gpt-6-sol"),
    ("openclaw", "openai", "gpt-6-sol"),
    ("openclaw", "anthropic", "claude-sonnet-5-5"),
    ("gemini_cli", "google", "gemini-2.5-pro"),
]


def workload():
    templates, _, _ = demo.workload()
    resources, snapshots = [], []
    for i, (client, provider, model) in enumerate(FLOWS):
        template = deepcopy(templates[i])
        task = f"multi-demo-{demo.DAY}-{i + 1:02}"
        session = f"multi-demo-{demo.DAY}-{client}-{i + 1:02}"
        trace = demo.ident(task + "-trace", 32)
        span_ids = {s["spanId"]: demo.ident(task + s["spanId"], 16) for s in template["scopeSpans"][0]["spans"]}
        for span in template["scopeSpans"][0]["spans"]:
            span["traceId"] = trace
            span["spanId"] = span_ids[span["spanId"]]
            if span.get("parentSpanId"):
                span["parentSpanId"] = span_ids[span["parentSpanId"]]
            a = {item["key"]: next(iter(item["value"].values())) for item in span["attributes"]}
            a.update(
                {
                    "service.name": "tracequota-multi-demo",
                    "tracequota.client.id": client,
                    "tracequota.client.version": "synthetic-1",
                    "tracequota.runtime": client,
                    "tracequota.surface": "cli",
                    "tracequota.integration_type": "tracequota_adapter",
                    "tracequota.billing_platform": provider,
                    "gen_ai.system": provider,
                    "session.id": session,
                    "tracequota.task.id": task,
                    "tracequota.task.title": f"Synthetic {client} / {provider} workload",
                    "project.name": "multi-client-workbench",
                    "tracequota.demo": True,
                }
            )
            if a.get("agent_id"):
                a["agent_id"] = span_ids.get(a["agent_id"], a["agent_id"])
                a["parent_agent_id"] = "main"
            if a.get("openinference.span.kind") == "LLM":
                # Only the explicitly multi-provider OpenClaw task changes provider per call.
                call_provider = "anthropic" if i == 2 and a.get("agent.type") == "subagent" else provider
                call_model = "claude-sonnet-5-5" if call_provider == "anthropic" else model
                a.update(
                    {
                        "gen_ai.system": call_provider,
                        "tracequota.billing_platform": call_provider,
                        "gen_ai.request.model": call_model,
                        "gen_ai.response.model": call_model,
                        "gen_ai.response.id": task + "-" + span["spanId"],
                        "tracequota.usage.input_uncached": int(a.pop("input_tokens")),
                        "tracequota.usage.output_semantics": "inclusive_reasoning",
                        "tracequota.usage.input_semantics": "uncached",
                        "tracequota.usage.reasoning": 100,
                    }
                )
                a.pop("cost_usd", None)  # Synthetic calculated value is not provider-reported evidence.
                if call_provider != "anthropic":
                    a.pop("tracequota.cache_write_ttl", None)
                if call_provider == "google":
                    a["cache_creation_tokens"] = 0
                    a["tracequota.usage.cache_storage_token_hours"] = 12000
            span["attributes"] = demo.attrs(a)
        template["resource"]["attributes"] = demo.attrs(
            {"service.name": "tracequota-multi-demo", "tracequota.client.id": client, "tracequota.demo": True}
        )
        resources.append(template)
        spans = template["scopeSpans"][0]["spans"]
        providers = {provider, "anthropic"} if i == 2 else {provider}
        for p in sorted(providers):
            for side, ns, used in [
                ("before", spans[0]["startTimeUnixNano"], 20),
                ("after", spans[0]["endTimeUnixNano"], 23),
            ]:
                snapshots.append(
                    {
                        "id": task + "-" + p + "-" + side,
                        "provider": p,
                        "account": "demo",
                        "task_id": task,
                        "session_id": session,
                        "captured_at": demo.utc(demo.datetime.fromtimestamp(int(ns) / 1e9, demo.timezone.utc)),
                        "source": "manual",
                        "demo": True,
                        "windows": [{"name": "5h", "used_percent": used}],
                    }
                )
    return resources, snapshots


def run():
    resources, snapshots = workload()
    with demo.httpx.Client(timeout=30) as client:
        for snapshot in snapshots:
            client.post(demo.API + "/api/quota/snapshots", json=snapshot).raise_for_status()
        client.post(demo.OTLP + "/v1/traces", json={"resourceSpans": resources}).raise_for_status()
    print("Synthetic multi-client demo: five tasks, including an OpenClaw task with two providers.")


if __name__ == "__main__":
    run()
