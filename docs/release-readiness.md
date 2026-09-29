# Private repository release readiness

This is the current publication/installation record for TraceQuota. Earlier implementation reports retain dated native-stack evidence and do not supersede this release check.

Repository: [ruanpato/tracequota](https://github.com/ruanpato/tracequota), **private**, primary branch **main**. Description: Local-first observability, token usage, API-equivalent costs, and quota intelligence for AI coding agents.

Topics: `ai-observability`, `claude-code`, `codex`, `developer-tools`, `docker`, `gemini-cli`, `llm`, `llm-cost`, `local-first`, `observability`, `openclaw`, `opentelemetry`, `otel`, `quota`, `self-hosted`, `token-usage`.

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
- Documentation: 37 Markdown files and 120 local links passed; 31 external targets checked (25 public URLs reachable, six local/private URLs verified separately).
- Publication files and Git history passed Gitleaks with zero secret findings. Ignored environment files, backups, dependencies and private local validation work are not published.

## Fresh installation

An authenticated clone of the private GitHub repository was tested in a separate Compose project with four empty volumes, no `.env` and default ports. The engine and downloaded image/build caches were reused; this was a clean application/storage installation, not a new operating-system installation.

The actual Quickstart commands passed: configuration, build/startup, doctor, demo, smoke, generic OTLP ingestion, browser inspection, shutdown, restart and persistence. The generic fixture kept incomplete cost visibly unknown. After restart, the ledger contained 26 tasks, 76 model calls and 52 quota snapshots on migration `0004` (25/75 from the main demo plus the generic fixture). The documented PostgreSQL backup/copy commands passed; restoration into a separate disposable database reproduced the same counts. Test database cleanup did not touch the application database.

The regular workspace stack was restored after the isolated test; its volumes were preserved. Machine-readable evidence is in [container-readiness.json](validation/container-readiness.json).

## GitHub verification

GitHub detects Apache-2.0, the README, contribution guide, code of conduct and pull-request template. The README HTML renders successfully and the root security policy was verified through authenticated access. Repository visibility, description, topics and default branch match the intended configuration. No README/license/ignore files were generated remotely.

The initial CI run exposed a nonexistent security-action tag and Windows checkout line endings. Both were corrected with a released, commit-pinned security action and `.gitattributes`. CI also avoids duplicate push/PR runs and cancels superseded runs on the same ref. Automatic dependency update proposals remain open for maintainer review; no upgrades were merged automatically.

The corrected [CI run](https://github.com/ruanpato/tracequota/actions/runs/36557703266) passed all eight jobs on commit `ad6afb9`: portable tests/lint/format/build on Ubuntu, macOS and Windows; PostgreSQL/migrations/dashboard SQL; Docker Compose pipeline/restart acceptance; dependency/secret scanning; and API/web builds for both Linux amd64 and arm64. The final documentation-only commit was validated locally and does not change the tested application.

The local repository began without commits or a remote. Initial publication uses a coherent implementation commit followed by useful CI corrections and this readiness record; no useful history was destroyed. The final local and remote `main` references are verified to match with a clean working tree.

Native coding-client certification and Docker Desktop runtime acceptance remain separate from these checks.

## Repository access

The private personal-account repository was created successfully. GitHub rejected the requested `pull` (read-only) collaborator invitation for `otaviopato` with HTTP 422. No invitation or write/admin access was granted. The owner chose to configure Otavio's access manually; this remains outside the automated validation.

## Scope and limits

An authenticated real Claude Code/Codex/OpenClaw/Gemini session requires the user's provider account and installed client/version. Synthetic and generic OTLP validation cannot certify it. The planned Copilot/OpenCode adapters are not shipped. No account tokens or model calls are needed for backend acceptance.

Windows/macOS Docker Desktop acceptance requires those runtimes. Linux amd64/arm64 application images are also built in CI; portable CI tests do not certify every native coding client or Desktop installation. The single-user stack remains localhost-only; public visibility does not make it a safe Internet service. Catalog coverage is finite, costs are estimates, and quota correlation is not causal attribution. Before a future public release, review these limits and any unresolved CI results. Do not change visibility as part of this phase.
