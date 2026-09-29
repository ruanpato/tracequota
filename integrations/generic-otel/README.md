# Generic OTLP integration

Send standard OTLP traces/logs/metrics to localhost:4318 (HTTP JSON/protobuf) or localhost:4317 (gRPC). API ingestion is internal; the Collector handles all signals and privacy. Annotate resource `service.name`, `project.name`, optional `session.id` and provider `gen_ai.provider.name` or legacy `gen_ai.system`.

Use `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.id` and `openinference.span.kind` where applicable. Generic input semantics are unknown unless explicitly declared with `tracequota.usage.input_semantics=inclusive|uncached`. Inclusive input is reduced only when both cache buckets are known and subtraction is nonnegative. Dedicated Claude Code input is already uncached. Missing quantities remain null. Preserve trace/span/parent IDs and stable request IDs. Agent identifiers/names improve attribution. Unknown models are unpriced. See the [canonical usage contract](../../docs/pricing/architecture.md).

Explicit identity/grouping annotations: `tracequota.client.id`, `tracequota.client.surface`, `tracequota.runtime.name`, `tracequota.integration.type`, `tracequota.task.id`, `tracequota.task.title`, `tracequota.account`. A root with `tracequota.task.kind=manual` and start/end timestamps brackets a manual task. Alternatively create/complete it through REST and attach its exact ID to emitted spans; client, workspace and session must match. Providers may differ across calls in one task. Do not put prompts or secrets in labels. Unsupported metadata is dropped.

```text
POST /api/tasks
{ "id": "issue-184", "client_id": "generic_otlp", "provider": "generic", "session_id": "session-1", "project": "my-project", "title": "Issue 184" }
POST /api/tasks/issue-184/complete
{ "status": "completed" }
```

Send `examples/generic-trace.json` with your HTTP client. macOS/Linux: `curl -H "Content-Type: application/json" --data-binary @examples/generic-trace.json http://localhost:4318/v1/traces`. PowerShell: `Invoke-RestMethod -Uri http://localhost:4318/v1/traces -Method Post -ContentType application/json -InFile examples/generic-trace.json`. This is a fixed dated synthetic fixture, separately labeled `demo=true`.

No gateway, reverse proxy or change to the model-provider endpoint is necessary. Other coding-agent adapters remain future work; protocol support does not imply native support for every agent product.
