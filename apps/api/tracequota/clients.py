# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Execution identity is independent of inference provider."""

CLIENTS = [
    (
        "claude_code",
        "Claude Code",
        "native_otel",
        "partial",
        "untested",
        "https://code.claude.com/docs/en/monitoring-usage",
    ),
    (
        "codex",
        "Codex",
        "native_otel",
        "partial",
        "untested",
        "https://learn.chatgpt.com/docs/config-file/config-advanced",
    ),
    (
        "openclaw",
        "OpenClaw",
        "plugin_otel",
        "provider_dependent",
        "untested",
        "https://docs.openclaw.ai/gateway/opentelemetry",
    ),
    (
        "gemini_cli",
        "Gemini CLI",
        "native_otel",
        "partial",
        "untested",
        "https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/telemetry.md",
    ),
    (
        "copilot_cli",
        "GitHub Copilot CLI",
        "tracequota_adapter",
        "experimental",
        "planned",
        "https://docs.github.com/en/copilot",
    ),
    ("opencode", "OpenCode", "plugin_otel", "experimental", "planned", "https://opencode.ai/docs/plugins/"),
    ("generic_otlp", "Generic OTLP", "tracequota_adapter", "partial", "synthetic_tested", None),
]


def identify(attrs, name=""):
    explicit = attrs.get("tracequota.client.id", attrs.get("tracequota.client.name", attrs.get("client.id")))
    if explicit:
        value = str(explicit).lower().replace(" ", "_").replace("-", "_")
        return {"claude": "claude_code", "openai_codex": "codex", "github_copilot_cli": "copilot_cli"}.get(value, value)
    service = str(attrs.get("service.name", "")).lower().replace("-", "_")
    event = str(attrs.get("event.name", name)).lower()
    for client in ("claude_code", "codex", "openclaw", "gemini_cli", "copilot_cli", "opencode"):
        if (
            service == client
            or (client == "openclaw" and service == "openclaw_gateway")
            or event.startswith(client + ".")
        ):
            return client
    if event.startswith("gemini."):
        return "gemini_cli"
    return "unknown"


def dimensions(attrs, name=""):
    client = identify(attrs, name)
    descriptor = next((d for d in CLIENTS if d[0] == client), None)
    return {
        "client_id": client,
        "client_version": attrs.get(
            "tracequota.client.version", attrs.get("service.version", attrs.get("app.version"))
        ),
        "surface": str(
            attrs.get(
                "tracequota.client.surface", attrs.get("tracequota.surface", attrs.get("source.surface", "unknown"))
            )
        ),
        "runtime": str(attrs.get("tracequota.runtime.name", attrs.get("tracequota.runtime", "unknown"))),
        "integration_type": str(
            attrs.get(
                "tracequota.integration.type",
                attrs.get("tracequota.integration_type", descriptor[2] if descriptor else "unknown"),
            )
        ),
        "workspace": str(attrs.get("tracequota.workspace", "local")),
        "billing_platform": str(attrs.get("tracequota.billing_platform", "unknown")),
        "service_tier": attrs.get("gen_ai.request.service_tier", attrs.get("tracequota.service_tier")),
        "region": attrs.get("cloud.region", attrs.get("tracequota.region")),
        "context_tokens": attrs.get("tracequota.context_tokens"),
        "cache_write_ttl": attrs.get("tracequota.cache_write_ttl"),
    }


def descriptors():
    return [
        {
            "id": i,
            "name": n,
            "integration_type": t,
            "validation": v,
            "source": s,
            "capabilities": {
                "model_calls": c,
                "tokens": c,
                "cache": "provider_dependent",
                "reasoning": "provider_dependent",
                "agents": "partial",
                "tools": c,
                "quota": "unsupported" if i != "claude_code" else "partial",
                "content_capture": "unsupported",
            },
        }
        for i, n, t, c, v, s in CLIENTS
    ]
