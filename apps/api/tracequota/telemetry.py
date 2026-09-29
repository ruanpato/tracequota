# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import base64
import hashlib
import json
from decimal import Decimal
from datetime import datetime, timezone

from .domain import CATEGORIES, utc
from .clients import dimensions
from .usage import KEYS, normalize

# This allowlist is shared with the Collector; arbitrary raw attributes never reach the ledger.
ALLOWED = set(
    """service.name service.version host.name gen_ai.system gen_ai.provider.name gen_ai.request.model gen_ai.response.model gen_ai.response.id gen_ai.usage.input_tokens gen_ai.usage.output_tokens llm.token_count.prompt llm.token_count.completion llm.token_count.prompt_details.cache_read llm.token_count.prompt_details.cache_write openinference.span.kind session.id prompt.id request_id client_request_id model input_tokens output_tokens cache_read_tokens cache_creation_tokens cost_usd cost_usd_micros duration_ms agent.name agent.type agent_id parent_agent_id query_source query_source_safe event.name event.timestamp event.sequence tool_name gen_ai.tool.name span.type source.surface project.name git.repository git.branch git.commit vcs.repository.url.full vcs.repository.name vcs.ref.head.name vcs.ref.head.revision type token.type token.count tracequota.task.id tracequota.task.title tracequota.project tracequota.account tracequota.demo tracequota.source_surface tracequota.status tracequota.task.kind tracequota.pricing.variant tracequota.cache_write_ttl""".split()
)

ALLOWED.update(k for keys in KEYS.values() for k in keys)
ALLOWED.update(
    "tracequota.client.id client.id tracequota.client.version app.version tracequota.surface tracequota.runtime tracequota.integration_type tracequota.workspace tracequota.billing_platform tracequota.service_tier gen_ai.request.service_tier tracequota.region cloud.region tracequota.context_tokens tracequota.usage.input_semantics tracequota.usage.output_semantics gen_ai.operation.name gen_ai.conversation.id tracequota.client.name tracequota.client.surface tracequota.runtime.name tracequota.integration.type conversation.id event.kind mcp.server.name gen_ai.tool.type".split()
)


def value(v):
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in v:
            return v[key]
    return None


def attributes(items):
    return {
        a["key"]: value(a.get("value", {}))
        for a in items
        if a.get("key") in ALLOWED and value(a.get("value", {})) is not None
    }


def identifier(raw, length):
    if not raw:
        return ""
    if len(raw) == length and all(c in "0123456789abcdefABCDEF" for c in raw):
        return raw.lower()
    try:
        return base64.b64decode(raw).hex()
    except ValueError:
        return ""


def timestamp(ns):
    return utc(datetime.fromtimestamp(int(ns) / 1e9, timezone.utc)) if ns else utc()


def digest(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def normalise(payload, signal):
    records = []
    plural = {"traces": "Spans", "logs": "Logs", "metrics": "Metrics"}[signal]
    for resource in payload.get("resource" + plural, []):
        rattrs = attributes(resource.get("resource", {}).get("attributes", []))
        for scope in resource.get("scope" + plural, []):
            if signal == "metrics":
                for metric in scope.get("metrics", []):
                    # Store observations for diagnostics; request ledger has precedence.
                    for container in ("sum", "gauge"):
                        for point in metric.get(container, {}).get("dataPoints", []):
                            attrs = {**rattrs, **attributes(point.get("attributes", []))}
                            records.append(
                                record(
                                    attrs,
                                    point,
                                    "metric",
                                    metric.get("name", "metric"),
                                    signal,
                                    {
                                        "metric_name": metric.get("name"),
                                        "value": point.get("asInt", point.get("asDouble", 0)),
                                        "temporality": metric.get(container, {}).get("aggregationTemporality"),
                                    },
                                )
                            )
                continue
            for raw in scope.get("spans" if signal == "traces" else "logRecords", []):
                attrs = {**rattrs, **attributes(raw.get("attributes", []))}
                name = attrs.get("span.type") or attrs.get("event.name", "") or raw.get("name", "")
                # Only use a log body as an event name when it is one of the known constant names.
                body = raw.get("body", {}).get("stringValue", "")
                if body in ("claude_code.api_request", "claude_code.tool_result", "claude_code.user_prompt"):
                    name = body
                if (
                    name in ("api_request", "claude_code.api_request", "claude_code.llm_request")
                    or attrs.get("openinference.span.kind") == "LLM"
                    or attrs.get("gen_ai.operation.name") in ("chat", "text_completion", "generate_content")
                    or (
                        name in ("codex.sse_event", "codex.websocket_event")
                        and attrs.get("event.kind") == "response.completed"
                    )
                ):
                    kind = "llm"
                elif (
                    name in ("tool_result", "claude_code.tool_result", "claude_code.tool")
                    or attrs.get("openinference.span.kind") == "TOOL"
                    or name in ("codex.tool_result", "gemini_cli.tool_call")
                ):
                    kind = "tool"
                elif name == "claude_code.interaction" or attrs.get("tracequota.task.kind"):
                    kind = "interaction"
                else:
                    kind = "metadata"
                if kind == "tool" and (attrs.get("mcp.server.name") or attrs.get("gen_ai.tool.type") == "mcp"):
                    kind = "mcp"
                records.append(record(attrs, raw, kind, name, signal))
    return records


def record(attrs, raw, kind, name, signal, extra=None):
    at = timestamp(raw.get("startTimeUnixNano", raw.get("timeUnixNano")))
    end = timestamp(raw["endTimeUnixNano"]) if raw.get("endTimeUnixNano") else None
    provider = str(
        attrs.get(
            "gen_ai.provider.name",
            attrs.get(
                "gen_ai.system",
                "anthropic" if str(name).startswith("claude_code") else "unknown",
            ),
        )
    )
    dims = dimensions(attrs, name)
    session = str(attrs.get("session.id", attrs.get("gen_ai.conversation.id", attrs.get("conversation.id", "unknown"))))
    request = attrs.get("gen_ai.response.id", attrs.get("request_id", attrs.get("client_request_id")))
    trace = identifier(raw.get("traceId", ""), 32)
    span = identifier(raw.get("spanId", ""), 16)
    # Use the same request identity across logs and traces; metric identity includes its timestamp.
    legacy_id = (
        digest(provider, session, "request", request)
        if request and kind == "llm"
        else digest(provider, session, kind, trace, span, at, attrs, extra)
    )

    event_id = digest(dims["workspace"], dims["client_id"], bool(attrs.get("tracequota.demo", False)), legacy_id)
    usage = normalize(attrs, dims["client_id"]) if kind == "llm" else {}
    # Deprecated activity fields are display-only; nullable canonical usage drives pricing.
    tokens = {
        k: usage.get(v) or 0
        for k, v in zip(CATEGORIES, ("input_uncached", "output_total", "cache_read", "cache_write"))
    }
    model = str(attrs.get("gen_ai.response.model", attrs.get("gen_ai.request.model", attrs.get("model", "unknown"))))
    sub = bool(
        attrs.get("agent_id")
        or attrs.get("agent.type") == "subagent"
        or str(attrs.get("query_source_safe", "")).startswith("agent.")
        or attrs.get("query_source") == "subagent"
        or attrs.get("agent.name") not in (None, "main")
    )
    agent = str(attrs.get("agent.name") or attrs.get("agent_id") or ("unnamed subagent" if sub else "main"))
    data = {
        **dims,
        "id": event_id,
        "legacy_id": legacy_id,
        "identity_version": 2,
        "usage": usage,
        "raw_metadata": attrs,
        "normalized_attributes": {**dims, "provider": provider, "model_resolved": model},
        "model_requested": attrs.get("gen_ai.request.model", attrs.get("model")),
        "model_resolved": model,
        "provider": provider,
        "session_id": session,
        "timestamp": at,
        "ended_at": end,
        "kind": kind,
        "signal": signal,
        "model": model,
        "agent": agent,
        "agent_type": "subagent" if sub else "main",
        "agent_id": attrs.get("agent_id"),
        "parent_agent_id": attrs.get("parent_agent_id"),
        "trace_id": trace,
        "span_id": span,
        "parent_span_id": identifier(raw.get("parentSpanId", ""), 16),
        "tokens": tokens,
        "attrs": attrs,
        "pricing": None,
        "provider_emitted_cost": format(Decimal(str(attrs["cost_usd"])), "f")
        if "cost_usd" in attrs
        else format(Decimal(str(attrs["cost_usd_micros"])) / Decimal(1000000), "f")
        if "cost_usd_micros" in attrs
        else None,
        "duration_ms": float(
            attrs.get(
                "duration_ms",
                (int(raw.get("endTimeUnixNano", 0)) - int(raw.get("startTimeUnixNano", 0))) / 1e6 if end else 0,
            )
        ),
        "status": "failed" if raw.get("status", {}).get("code") in (2, "STATUS_CODE_ERROR") else "completed",
        "demo": bool(attrs.get("tracequota.demo", False)),
    }
    return {**data, **(extra or {})}


def sanitise_traces(payload):
    """Final Phoenix boundary: also strip scope/schema/link content unsupported by OTTL allowlisting."""

    def safe_attrs(items):
        return [item for item in items if item.get("key") in ALLOWED and value(item.get("value", {})) is not None]

    resources = []
    for resource in payload.get("resourceSpans", []):
        scopes = []
        for scope in resource.get("scopeSpans", []):
            spans = []
            for span in scope.get("spans", []):
                a = attributes(span.get("attributes", []))
                safe = {
                    key: span[key]
                    for key in (
                        "traceId",
                        "spanId",
                        "parentSpanId",
                        "startTimeUnixNano",
                        "endTimeUnixNano",
                        "kind",
                        "flags",
                    )
                    if key in span
                }
                safe["name"] = str(a.get("span.type", a.get("openinference.span.kind", "agent.span")))
                safe["attributes"] = safe_attrs(span.get("attributes", []))
                safe["status"] = {"code": span.get("status", {}).get("code", 0)}
                safe["links"] = [
                    {k: link[k] for k in ("traceId", "spanId", "flags") if k in link} for link in span.get("links", [])
                ]
                spans.append(safe)
            scopes.append({"scope": {"name": "tracequota.metadata"}, "spans": spans})
        resources.append(
            {
                "resource": {"attributes": safe_attrs(resource.get("resource", {}).get("attributes", []))},
                "scopeSpans": scopes,
            }
        )
    return {"resourceSpans": resources}
