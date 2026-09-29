# Quickstart

Run the complete local stack from a clean checkout with Git, Docker and Compose. Host Python, Node.js, model API keys and coding-client installations are not required. The repository is initially private: authenticate to GitHub and accept your repository invitation before cloning. Never put access tokens in clone URLs or configuration.

## 1. Confirm prerequisites

Start Docker Desktop on macOS or Windows 11/WSL2 using Linux containers, or Docker Engine with the Compose plugin on Linux. Colima is an alternative macOS runtime.

```bash
git --version
docker version
docker compose version
```

`docker version` must show a **Server** section. Compose must be v2.24 or later. A missing socket/server means Docker is not running. Allow several GiB of free disk and around 3–4 GiB of memory for a small demo stack; builds and larger workloads can need more. Images support Linux amd64/arm64; the [release report](release-readiness.md) identifies the tested platform.

## 2. Clone and start

These commands work in a Unix shell or PowerShell:

```bash
git clone https://github.com/ruanpato/tracequota.git
cd tracequota
docker compose up -d --build --wait --wait-timeout 300
```

No `.env` is needed. First startup downloads images, builds API/web, creates four persistent volumes, migrates the database and syncs bundled prices. Optional ports/passwords are explained in [configuration](configuration.md). Keep the loopback-only network boundary.

## 3. Verify health

```bash
docker compose ps
docker compose run --rm tracequota-doctor
```

Doctor checks API, Collector, Phoenix, Prometheus and Grafana; every check must print `PASS`. The Collector's distroless image has no shell probe, so doctor checks its health extension. The other main services have Compose health checks.

Open [TraceQuota](http://localhost:8080), [Grafana](http://localhost:3000) and [Phoenix](http://localhost:6006). An empty dashboard is expected until telemetry arrives. Optional HTTP check:

```bash
curl -f http://localhost:8080/health
```

In PowerShell use `Invoke-RestMethod http://localhost:8080/health`. A healthy response includes `status: healthy` and the API version.

## 4. Observe synthetic data

```bash
docker compose run --rm tracequota-demo
docker compose run --rm tracequota-smoke
```

Select **Demo data**. Inspect tasks, token/cost components, the mixed OpenClaw task's two providers, and trace IDs in Phoenix. The demo contains 25 tasks, 75 model calls, 15 sessions and 52 synthetic/manual quota snapshots. Smoke verifies replay, pricing/quotas, filters, Phoenix, Prometheus and Grafana. Export/scrape checks may wait briefly. Same-date replay is idempotent; pin a date with `docker compose run --rm -e DEMO_DATE=2026-09-28 tracequota-demo` for repeated acceptance runs.

A minimal generic OTLP client can send the included safe fixture from the checkout:

```bash
curl -f -H "Content-Type: application/json" --data-binary @examples/generic-trace.json http://localhost:4318/v1/traces
```

PowerShell:

```powershell
Invoke-RestMethod -Uri http://localhost:4318/v1/traces -Method Post -ContentType application/json -InFile examples/generic-trace.json
```

This dated synthetic fixture omits some usage semantics, so partial/unknown pricing is expected. It demonstrates OTLP ingestion, not an authenticated native client. See [generic conventions](../integrations/generic-otel/README.md).

## 5. Connect an actual coding client

Choose a [client guide](README.md#client-guides): Claude Code, Codex, OpenClaw or Gemini CLI. Point the host client's documented exporter to `http://localhost:4318` or gRPC port 4317. Some exporters require `/v1/logs`; follow the selected guide. Merge settings rather than replacing user files, keep content logging off, then restart that client. Update endpoints if ports changed.

Run your normal work. TraceQuota does not log in, invoke a model or consume quota on your behalf. Select **Live data**, inspect Integrations for last-seen telemetry, and check Tasks/Grafana. Metrics-only signals cannot populate a complete request ledger or Phoenix traces. Native client/version validation is separate from synthetic tests; planned Copilot/OpenCode adapters cannot be enabled as if shipped.

Unknown quantities are not zeros. API-equivalent cost is an estimate, not a subscription bill. Quota requires independent provider/account evidence. Read [pricing semantics](pricing/architecture.md).

## 6. Verify persistence

After the demo:

```bash
docker compose down
docker compose up -d --wait --wait-timeout 300
docker compose run --rm tracequota-doctor
docker compose run --rm tracequota-doctor python tools/persistence.py
```

Tasks and quota must survive. **Do not add `-v` to shutdown:** it erases all four volumes. Review [backups/updates](configuration.md) before upgrades or resets.

## Startup diagnosis and coding-agent checklist

- No Docker server: start the runtime; check `docker version` and `docker context ls`.
- Port conflict: override that port in `.env`, restart and update host exporter endpoints.
- Download/build failure: check Internet access, registry limits and disk space.
- API unhealthy: inspect `docker compose logs --tail 100 tracequota-api postgres` for migration/catalog errors; do not remove volumes.
- No data: check exporter signal/endpoint, client version and UI data-source selection.

An agent should run prerequisite checks first, stop dependent steps on failure, inspect targeted logs, and rerun health checks after correction. Report actual URLs and whether data is synthetic or live. Do not claim native-client support or healthy containers from configuration validation alone. Never use deletion, port exposure, replacement of existing client settings, provider login or a real model invocation as an automatic recovery step. See [troubleshooting](troubleshooting/README.md).
