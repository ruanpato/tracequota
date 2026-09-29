# Claude Code onboarding

Sources and version notes: [monitoring](https://code.claude.com/docs/en/monitoring-usage), [hooks](https://code.claude.com/docs/en/hooks), [status line](https://code.claude.com/docs/en/statusline), [Desktop](https://code.claude.com/docs/en/desktop). Researched 2026-09-28. These are documentation-backed instructions; live provider execution is not claimed as verified. No Claude installation/auth configuration is modified by TraceQuota.

## CLI — macOS and Linux

Start the backend: `docker compose up -d`. In the terminal where you run Claude:

```sh
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_METRICS_INCLUDE_ACCOUNT_UUID=false
export OTEL_LOG_USER_PROMPTS=0
export OTEL_LOG_ASSISTANT_RESPONSES=0
export OTEL_LOG_TOOL_DETAILS=0
export OTEL_LOG_TOOL_CONTENT=0
export OTEL_LOG_RAW_API_BODIES=0
export OTEL_RESOURCE_ATTRIBUTES="project.name=my-project,tracequota.source_surface=claude-code-cli"
claude
```

Keep session IDs enabled (the upstream default). Native metrics remain separate from request accounting. Events let the ledger show token requests and interaction correlation. Optional repository identity: `OTEL_METRICS_INCLUDE_REPOSITORY=true` on a runtime that supports it. Consider whether repository labels are sensitive.

## CLI — Windows PowerShell

Use Docker Desktop with its WSL2 backend and Linux containers. In the same PowerShell window as Claude:

```powershell
$env:CLAUDE_CODE_ENABLE_TELEMETRY = "1"
$env:OTEL_METRICS_EXPORTER = "otlp"
$env:OTEL_LOGS_EXPORTER = "otlp"
$env:OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"
$env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4318"
$env:OTEL_METRICS_INCLUDE_ACCOUNT_UUID = "false"
$env:OTEL_LOG_USER_PROMPTS = "0"
$env:OTEL_LOG_ASSISTANT_RESPONSES = "0"
$env:OTEL_LOG_TOOL_DETAILS = "0"
$env:OTEL_LOG_TOOL_CONTENT = "0"
$env:OTEL_LOG_RAW_API_BODIES = "0"
$env:OTEL_RESOURCE_ATTRIBUTES = "project.name=my-project,tracequota.source_surface=claude-code-cli"
claude
```

If Claude runs inside WSL rather than native Windows, use the Linux example there and verify WSL localhost forwarding to Docker Desktop. Do not change container networking to host mode.

## Optional beta execution traces

For runtimes supporting the documented tracing beta, add:

```sh
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp
```

PowerShell:

```powershell
$env:CLAUDE_CODE_ENHANCED_TELEMETRY_BETA = "1"
$env:OTEL_TRACES_EXPORTER = "otlp"
```

Restart Claude. Trace trees now go to Phoenix. Beta field availability varies by version; TraceQuota does not enable detailed/content tracing. Open a task, copy its trace ID and use Phoenix's trace filter. V1 links to Phoenix's UI instead of assuming an unstable project-specific deep-link route. Request IDs deduplicate logs and spans when available. Without shared IDs, exact request correlation is limited.

## Claude Desktop → Code → Local

Select **Code**, choose **Local** in the environment dropdown, hover Local and open its gear editor. Set the same key/value pairs above there, optionally including beta flags, and start a new Local session. Desktop may not inherit shell exports. Alternatively merge the provided `integrations/claude-code/settings.example.json` **env** keys into your user settings file; do not replace existing settings. A repository's `.claude/settings.json` is not a supported place to enable exporter destinations under current security rules.

Desktop Code Local is supported by current official configuration documentation, but must be validated on your installed runtime with actual telemetry. Normal Chat/Cowork are not equivalent surfaces. Cloud and SSH sessions need reachable collectors in their own environment; `localhost` there is not your laptop. TraceQuota V1 does not claim those surfaces.

## Optional session lifecycle hooks

Merge `integrations/claude-code/hooks.example.json` into user settings. It uses HTTP hooks on SessionStart/SessionEnd, requires no host binary and sends to the local API at port 8080. The API discards prompt/transcript/cwd fields and returns a non-blocking empty JSON object. These hooks bracket **session activity**, not feature tasks. They do not implement `Stop` as a reliable feature completion primitive.

## Optional official quota status-line adapter

Supported Claude versions (v2.1.251+) can pass documented `rate_limits` fields to status-line commands for eligible subscriptions after an API response. This optional adapter needs host Python 3; the core backend and manual quota UI do not. Place the repo at any path and merge an appropriate statusLine setting into user settings:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 \"/absolute/path/to/tracequota/integrations/claude-code/statusline.py\""
  }
}
```

On Windows use `python` and your escaped path, for example `python \"C:\\dev\\tracequota\\integrations\\claude-code\\statusline.py\"`. This is a user-selected path; TraceQuota contains no machine-specific absolute path. Avoid overwriting an existing status line: integrate the adapter's `forward` function into your existing script if desired. `TRACEQUOTA_URL` can override the local endpoint for a changed web port.

The script receives JSON on stdin, forwards only session ID plus used_percentage/resets_at for five_hour and seven_day, and prints a simple status. No Anthropic requests, credential access, artificial model usage or independent refresh loop occur. Refresh follows provider status-line invocation; unavailable fields are omitted. Source is **official payload**, while transport and capture are TraceQuota's adapter. Account defaults to `default`; for multiple accounts use manual snapshots or extend the adapter with explicit account mapping. Capture after the first request cannot supply a pre-task snapshot for that first request.

## Verify

Run Claude normally. Check Integrations for last-seen real telemetry, Tasks for interactions, and Grafana for `claude_code` metrics. Keep live data selected so synthetic records cannot be mistaken for provider evidence. If there is no beta trace, Phoenix will not magically contain a tree from metrics alone. Use `docker compose run --rm tracequota-doctor` and the troubleshooting guide. No onboarding commands log into a provider or modify user auth.

## Multi-client identity and pricing

The existing Claude paths remain intact. Claude Code is now a client dimension, independent from Anthropic provider identity. Explicit Claude service/event signals establish the client; Anthropic alone does not. New safe namespaces include `tracequota.client.name`, `.version`, `.surface`, `tracequota.runtime.name` and `tracequota.integration.type`. Live native CLI/Desktop validation remains untested; synthetic data does not change that state.

Dedicated Claude `input_tokens` is uncached. Cache reads/writes remain separate, missing quantities are nullable, and unreported cache write TTL makes that cost component partial rather than assuming a five-minute charge. The bundled Anthropic JSON catalog freezes rule/hash/component provenance on new calls. Historical estimates survive migration and sync. Tier, platform and region are evaluated separately; unsupported cloud-platform rules remain unknown. Provider-emitted estimates and API-equivalent workload value are distinct from subscription invoices and sourced quota evidence. See [pricing architecture](../pricing/architecture.md).
