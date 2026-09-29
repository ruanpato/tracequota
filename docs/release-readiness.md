# Private repository release readiness

This is the current publication/installation record for TraceQuota. Earlier implementation reports retain dated native-stack evidence and do not supersede this release check.

Repository: `ruanpato/tracequota`, private, primary branch `main`. Description: Local-first observability, token usage, API-equivalent costs, and quota intelligence for AI coding agents.

Copyright 2026 Ruan Pato. Apache-2.0 with a project NOTICE, source attribution and image license metadata. All project content uses English (en-US); UI timestamps explicitly use UTC. No i18n framework or unrelated accessibility work was added.

The README, Quickstart, configuration/backups/updates, development, documentation index, contribution and security guides were reviewed against the implementation. Generic usage/cache assumptions and outdated pricing/roadmap text were corrected. Private telemetry, auth files, dependencies, builds, dumps and logs are excluded from publication. Curated screenshots/evidence use synthetic data.

## Validation status

Local validation passed on macOS with Colima and a Linux arm64 Docker engine:

- Python 3.12 backend: 77 SQLite tests and 77 PostgreSQL tests passed; lint and formatting passed.
- Node.js 24 frontend: 5 tests, TypeScript lint, formatting and production build passed.
- Python/npm dependency audits: no known vulnerabilities reported at check time.
- Container build/startup: seven services running, all six configured health checks healthy; doctor also verifies the Collector.
- Pipeline smoke: 25 synthetic tasks, 75 model calls and 52 quota snapshots; replay, mixed-provider costs, client/provider filters, Phoenix and Prometheus passed.
- Grafana: 34 panels and 99 SQL query combinations passed against PostgreSQL.
- Generic OTLP fixture accepted; missing usage semantics remain visibly unknown/unpriced.
- Shutdown/restart without volume removal preserved task and quota records.
- Documentation: 37 Markdown files, 118 local links and 30 public external links validated.
- Publication candidate secret scan passed; a final commit/history scan is required before push.

The clean-clone installation and remote metadata/CI checks are recorded below when completed. Checks still pending are not represented as passed.

## Repository access

The private personal-account repository was created successfully. GitHub rejected the requested `pull` (read-only) collaborator invitation for `otaviopato` with HTTP 422. No invitation or write/admin access was granted. The owner chose to configure Otavio's access manually; this remains outside the automated validation.

## Scope and limits

An authenticated real Claude Code/Codex/OpenClaw/Gemini session requires the user's provider account and installed client/version. Synthetic and generic OTLP validation cannot certify it. The planned Copilot/OpenCode adapters are not shipped. No account tokens or model calls are needed for backend acceptance.

Windows/macOS Desktop acceptance and Linux amd64 builds require their respective runtimes/CI; a local arm64 check cannot certify every platform. The single-user stack remains localhost-only; public visibility does not make it a safe Internet service. Catalog coverage is finite, costs are estimates, and quota correlation is not causal attribution. Before a future public release, review these limits and any unresolved CI results. Do not change visibility as part of this phase.
