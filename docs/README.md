# Documentation and repository map

Start with [Quickstart](quickstart.md), then [configuration/backups/updates](configuration.md) and [troubleshooting](troubleshooting/README.md). Source and documentation use English (en-US); the interface supports en-US and pt-BR with lightweight translation catalogs.

## Client guides

- [Claude Code CLI and Desktop Local](integrations/claude-code.md)
- [Cursor metadata hooks](integrations/cursor.md)
- [Set up with a coding agent](integrations/agent-setup.md)
- [Codex](integrations/codex.md)
- [OpenClaw](integrations/openclaw.md)
- [Gemini CLI](integrations/gemini-cli.md)
- [Generic OTLP](../integrations/generic-otel/README.md)
- [Planned Copilot CLI](integrations/copilot-cli.md) and [planned OpenCode](integrations/opencode.md)

## Design and contributions

- [Architecture](../ARCHITECTURE.md) and [migration strategy](migrations/multi-client-pricing.md)
- [Pricing/usage semantics](pricing/architecture.md), [catalogs](../pricing/README.md) and [pricing contributions](pricing/contributing.md)
- [Development](development.md), [contribution guide](../CONTRIBUTING.md), [security](../SECURITY.md) and [privacy](privacy.md)
- [License](../LICENSE), [notice](../NOTICE), [changelog](../CHANGELOG.md) and [roadmap](../ROADMAP.md)

## Repository map

| Path | Purpose |
|---|---|
| `apps/api` | FastAPI, domain/telemetry normalization, analytics, pricing CLI, SQLAlchemy and Alembic |
| `apps/web` | React/TypeScript dashboard and Nginx runtime |
| `integrations` | Safe generic conventions, Claude configuration fragments and optional status-line adapter |
| `packages` | Domain/telemetry interface documentation; executable modules ship inside the API |
| `pricing` | JSON Schema, provider catalogs and pricing changelog |
| `infrastructure` | Collector, PostgreSQL role, Phoenix, Prometheus and Grafana provisioning |
| `dashboards` | Provisioned Grafana dashboard |
| `examples` | Deliberately synthetic OTLP and multi-client workloads |
| `tests` | Backend domain/API/migration/privacy/pricing tests; frontend tests live in `apps/web/src` |
| `tools` | Doctor, smoke, persistence, container acceptance and documentation/image validation |
| `.github` | CI, dependency updates and PR template |
| `docs` | User/developer guides, sourced research and curated screenshots/validation evidence |

## Validation and historical evidence

[Dependency/UI follow-up](hardening-report.md) records the latest validation. [Release readiness](release-readiness.md) retains the initial publication/installation record. [Multi-client implementation](multi-client-report.md) and [initial V1 implementation](implementation-report.md) retain dated evidence and limitations; they are historical records, not current Quickstart instructions. Curated `validation/` and `screenshots/` files use synthetic/local test data. Temporary logs, live databases, environment files, dependencies and build outputs are ignored.

[Upstream capability research](research/current-capabilities.md) records documentation provenance. [Landscape research](research/landscape.md) explains design choices without claiming live integration certification.

Current container and fresh-install evidence: [container-readiness.json](validation/container-readiness.json).
