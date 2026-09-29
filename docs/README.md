# Documentation and repository map

Start with [Quickstart](quickstart.md), then [configuration/backups/updates](configuration.md) and [troubleshooting](troubleshooting/README.md). Project content is English (en-US); this release does not add an i18n framework.

## Client guides

- [Claude Code CLI and Desktop Local](integrations/claude-code.md)
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

[Release readiness](release-readiness.md) is the current publication/installation record. [Multi-client implementation](multi-client-report.md) and [initial V1 implementation](implementation-report.md) retain dated evidence and limitations; they are historical records, not current Quickstart instructions. Curated `validation/` and `screenshots/` files use synthetic/local test data. Temporary logs, live databases, environment files, dependencies and build outputs are ignored.

[Upstream capability research](research/current-capabilities.md) records documentation provenance. [Landscape research](research/landscape.md) explains design choices without claiming live integration certification.
