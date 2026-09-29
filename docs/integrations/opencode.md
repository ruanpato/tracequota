# OpenCode → TraceQuota

Status: **planned / experimental** plugin descriptor. No TraceQuota OpenCode plugin is shipped, and no native OpenCode runtime has been tested. [Official plugin documentation](https://opencode.ai/docs/plugins/) describes an extension surface; it is not proof of a working telemetry integration.

A future plugin should emit safe OTLP through the existing Collector with `tracequota.client.id=opencode`, surface=terminal, runtime identity, client/plugin versions and integration type `plugin_otel`. Capture actual provider and resolved model per call: OpenCode may use multiple providers. Measure usage using documented upstream semantics and preserve source keys; missing cache or reasoning quantities remain nullable. Do not record tool arguments/results, prompts, responses or credentials.

The canonical domain and catalog need no redesign for this client. Add detector/normalizer fixtures, live export tests, capability evidence and onboarding before changing the descriptor's validation state. Provider/account quota evidence remains independent from client identity. Public API-equivalent estimates do not establish a subscription bill. Use the same existing Compose stack on macOS/Linux/Windows.
