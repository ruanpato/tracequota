# OpenClaw → TraceQuota

Status: upstream official diagnostics OTel plugin documented; TraceQuota live integration **untested**, capabilities **provider dependent**. Checked 2026-09-28 against [OpenTelemetry export](https://docs.openclaw.ai/gateway/opentelemetry), [setup](https://docs.openclaw.ai/gateway/opentelemetry/setup) and [configuration](https://docs.openclaw.ai/gateway/opentelemetry/configuration).

Use the existing stack and enable the official `diagnostics-otel` plugin plus diagnostics export according to the setup page. Point its OTLP/HTTP protobuf endpoint to `http://localhost:4318`. Both the diagnostics surface and plugin need enabling. Review content capture settings in the upstream privacy guide; TraceQuota's Collector independently strips content. The descriptor uses `plugin_otel` because current upstream export is provided by that official plugin.

Keep OpenClaw client identity separate from provider metadata. Supply `tracequota.client.id=openclaw`, surface=gateway and runtime identity in safe attributes when native metadata is ambiguous. Preserve the real provider/model and billing platform on every call. Do not price AWS/Azure/other platforms as direct APIs. Native model/cache semantics vary by provider; use explicit canonical usage rather than subtracting cache from an unknown counter.

A single task may contain OpenAI and Anthropic model calls, nested agents and tools. The synthetic demo demonstrates exactly that and independently filterable client/provider costs. A gateway on another machine needs a reachable, deliberately configured Collector; its `localhost` refers to that machine. Cross-platform host clients still use the same TraceQuota Compose services.

No OpenClaw-specific official quota retrieval is implemented. Quota snapshots remain independent provider/account evidence. Synthetic quota examples are manual demo data and do not reveal any real quota.
