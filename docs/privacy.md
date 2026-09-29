# Privacy

TraceQuota sends no analytics and requires no account. During normal operation all storage and telemetry exporters remain in the local Compose network. Initial image/dependency downloads and optional security/manifest checks contact public registries. The optional status-line adapter sends selected quota fields only to localhost and never contacts Anthropic.

## Data retained
PostgreSQL: timestamps, provider/model, session/prompt/request/trace/span/agent IDs, agent and tool names, metadata-only service/host/project/repository/branch/commit labels, status/duration, token counts, pricing rates and estimates, quota percentages/reset times/source/account. Synthetic demo records carry `demo=true`. Repository/host/agent labels can still be sensitive. Snapshot captures can be stale. Prometheus and Grafana retain metrics/dashboard state. Phoenix retains **sanitized** spans and parent relationships.

## Data discarded
Default Collector processors remove unknown attributes, log bodies, span events, status messages and free-form span names. Prompt text, responses, source-file contents, shell commands/output, tool arguments and credentials are excluded from the allowlist. The internal Phoenix relay also removes scope attributes, span-link attributes, trace-state and events before exporting traces. The ledger repeats attribute filtering and ignores hook transcript/prompt/cwd bodies. No raw payload is stored. This is field-based sanitization, not a universal secret scanner: do not put secrets in permitted metadata labels. Collector memory briefly holds inbound data before filtering. Existing historical records are not retroactively erased by changing configuration.

## Rich capture
V1 has no UI toggle for rich capture. Explicit opt-in means creating a separate Collector configuration, reviewing its exporters and data retention, and replacing the mounted configuration yourself. The default API continues to reject unknown content. If you preserve rich spans for Phoenix, they may contain source code and secrets; consent is per deployment and does not alter the default. Follow provider-side content gates as well.

## Storage and removal
Named Docker volumes hold PostgreSQL, Phoenix, Prometheus and Grafana state. `docker compose down` retains them. **`docker compose down -v` permanently removes persistent local data.** Back up volumes/database dumps before resets. Local test environments and screenshots may also contain synthetic metadata. There is no automated retention job in V1.
