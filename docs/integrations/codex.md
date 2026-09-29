# Codex → TraceQuota

Status: upstream native OpenTelemetry documented; TraceQuota live integration **untested**. Synthetic Codex completion calls test the canonical contract, not authentication or your installed Codex version. Checked 2026-09-28 against [official advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced).

Keep the existing local stack running. Add an opt-in exporter to the Codex configuration used by your CLI:

```toml
[otel]
log_user_prompt = false
exporter = { otlp-http = { endpoint = "http://localhost:4318/v1/logs", protocol = "binary" } }
```

Restart that Codex process after changing its configuration. This file-based setting works across macOS/Linux/Windows; do not infer that a Desktop session uses the same configuration file. Do not export credentials or enable prompt logging. Codex emits request/stream/tool events; a request-start log alone does not establish completed usage. TraceQuota recognizes completed stream events when `event.kind=response.completed` and canonical token fields are present. Metrics remain separate from model-call totals.

Check Integrations for **live** telemetry and inspect task/event metadata. Missing provider, resolved model, cache quantities, tier or billing platform stays unknown/partial. Codex is the client; OpenAI is only one possible model provider. Native field variations may require an adapter mapping to the [canonical dimensions and usage contract](../pricing/architecture.md). `examples/multi_client_demo.py` demonstrates explicit client=codex/provider=openai data without using your account.

No official Codex quota collector is shipped. Use independently sourced provider/account manual snapshots. API-equivalent workload value is not a ChatGPT subscription charge.
