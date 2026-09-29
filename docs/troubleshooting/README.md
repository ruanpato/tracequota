# Troubleshooting

Start with `docker compose ps`, `docker compose logs --tail 100`, and `docker compose run --rm tracequota-doctor`. A missing Docker socket means the engine is stopped or absent: install/start Docker Desktop (macOS/Windows), or Docker Engine plus Compose plugin (Linux). The Docker CLI alone cannot launch Linux containers on macOS. Check `docker context ls` and select the intended runtime yourself.

Port conflicts: set optional WEB_PORT, GRAFANA_PORT, PHOENIX_PORT, PROMETHEUS_PORT, OTLP_GRPC_PORT or OTLP_HTTP_PORT in `.env`. Update host telemetry/status-line endpoint accordingly. Compose defaults need no `.env`. The API's displayed tool links follow the configured public ports.

No requests in TraceQuota: enable `OTEL_LOGS_EXPORTER=otlp`; metric-only telemetry appears in Prometheus and metric observations, not request/task totals. Keep session identifiers enabled. An older Claude may omit prompt/request/agent IDs or lack tracing. For Phoenix, enable the documented beta tracing flags or use generic OTLP. Use a new Desktop Local session after editing the environment. Check for managed settings that pin a different endpoint.

A running task may mean no completion signal was received. Session hooks do not define feature tasks. Logs without trace context cannot link to Phoenix. Use explicit manual IDs for reliable external task grouping.

Missing quota: eligible supported Claude sessions expose status-line windows after the first API response; other accounts/surfaces may not. Manual entry always works. A reset crossing deliberately has no numeric delta. A snapshot too far from the start/end is omitted. Missing pricing is **unpriced**, never free.

Grafana SQL permission errors: the read-only role is created when PostgreSQL's volume is first initialized. Reusing an unrelated preexisting database needs equivalent SELECT permissions; do not destroy existing data to fix permissions. Changing .env passwords does not rotate existing database/Grafana credentials in persistent volumes.

Report sanitized logs and versions. Never paste authentication tokens, prompts or raw transcripts into issues.
