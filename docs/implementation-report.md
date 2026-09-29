# TraceQuota V1 implementation report

Historical initial-build report. The [multi-client and versioned-pricing report](multi-client-report.md) documents the current 0.2 implementation and supersedes the domain, pricing, client coverage and dashboard counts below.

Implementation and local validation: 2026-09-28. This repository implements a usable MVP, with observed test evidence separated from pending acceptance. It has not been published to GitHub or GHCR. The full Docker definition of done is **not yet verified**: the installed Docker CLI has no reachable Engine or Desktop runtime. Checking both configured contexts found missing engine sockets; no Docker Desktop application or alternate installed runtime was found.

## What was built

A local, Apache-2.0 observability application with a persistent task/request/quota ledger; metadata-only OTLP ingestion; Claude Code and generic agent normalization; versioned API-equivalent cost calculations; main/subagent and model breakdowns; seven React pages; task investigation; manual and estimated quota forms; optional documented official status-line quota capture; Phoenix trace connectivity; provisioned Prometheus/Grafana; deterministic synthetic telemetry; health, doctor, smoke and persistence tools; migrations; cross-platform CI; and contribution, privacy, security, research and onboarding documentation.

Settings describes the active privacy/storage/pricing configuration and links. It does not expose a switch that silently enables content capture. Rich capture requires a reviewed alternative configuration.

## Architecture and repository structure

The canonical deployment is Docker Compose. Agents stay on the host and send telemetry to loopback ports 4317/4318. The seven main services are PostgreSQL, TraceQuota API, TraceQuota web, OpenTelemetry Collector, Phoenix, Prometheus and Grafana. Four named volumes persist the databases and time-series/UI state. Tool services use an optional Compose profile and do not start with normal startup.

| Path | Responsibility |
|---|---|
| `apps/api` | FastAPI/Pydantic domain, SQLAlchemy storage, Alembic, OTLP normalization, analytics |
| `apps/web` | React/TypeScript/Vite UI; static Nginx runtime |
| `integrations/claude-code` | Environment/hooks examples and optional Python status-line adapter |
| `integrations/generic-otel` | Standard OTLP conventions and example ingestion |
| `packages/domain`, `packages/telemetry` | Interface documentation; executable modules currently ship in the API |
| `infrastructure` | Collector, PostgreSQL, Prometheus, Grafana and Phoenix configuration |
| `dashboards` | Provisioned 23-panel Grafana dashboard |
| `examples` | Deterministic demo and generic synthetic OTLP fixture |
| `tools` | Doctor, full/native smoke, persistence, SQL and architecture-manifest checks |
| `tests` | Domain, ingestion, quota, API, privacy, database and configuration tests |
| `docs` | Research, onboarding, troubleshooting, privacy, screenshots and validation evidence |
| `.github` | Portable tests, PostgreSQL, Compose acceptance, multiarch builds and security workflows |

Domain and telemetry packages remain normal Python modules inside the API to avoid unnecessary packaging complexity in V1. Phoenix owns a separate SQLite database/volume; the TraceQuota ledger uses PostgreSQL. Detailed diagrams and boundaries are in [ARCHITECTURE.md](../ARCHITECTURE.md).

## Telemetry flow

1. A host agent exports OTLP HTTP JSON/protobuf or gRPC to the Collector.
2. Collector pipelines remove unsupported attributes and content; log bodies are emptied, status messages cleared, free-form span names replaced and span events dropped.
3. The ledger exporter sends filtered traces/logs/metrics to the internal API. Request usage and native metric observations are stored separately, preventing counter exports from doubling request totals.
4. The Phoenix exporter sends traces through a dedicated internal API privacy route, which also sanitizes scope metadata, span-link content and trace-state, then forwards protobuf traces to Phoenix. This route carries telemetry only; no model-provider traffic passes through TraceQuota.
5. Prometheus scrapes both the Collector metrics exporter and the ledger's normalized metrics endpoint. Delta metric observations are converted to cumulative data in the Collector.
6. Grafana provisions Prometheus and a read-only PostgreSQL datasource plus the dashboard automatically. The React UI queries the ledger; a task exposes its trace ID and Phoenix UI link.

OTLP JSON/protobuf bodies are limited to 4 MiB, including bounded gzip expansion. Database failures return retryable errors. PostgreSQL advisory transaction locks serialize ingestion writes. Collector retries are bounded and do not provide a durable disk queue in V1.

## Task correlation

The hierarchy is provider → project → session → task → request/tool/agent metadata. An explicit `tracequota.task.id` groups a manual task; REST can create and complete it, including initial/final Git metadata. Otherwise `prompt.id` or a trace ID represents an interaction. ID-less telemetry is labeled session activity. SessionStart/SessionEnd hooks bracket a session; a Stop event is not treated as reliable feature completion.

Request identity uses provider, session and stable request ID when supplied; logs and spans of the same request merge without double counting. Missing shared IDs constrain exact correlation. Parent trace/span IDs remain available in Phoenix. Main, named and unnamed subagents are distinguished, with model and four token-category totals. Late telemetry updates usage without reopening a completed task. Missing completion remains running rather than inventing a duration.

Repository, branch and commit data are metadata supplied by the agent/integration or manual task API. TraceQuota does not automatically inspect host repositories or infer a GitHub issue from a prompt. Phoenix links open its UI and provide a related trace ID; stable project-specific trace deep links are deferred.

## Quota and cost semantics

| Evidence | Implemented behavior |
|---|---|
| Official provider telemetry | Documented Claude metrics/events and generic request usage, normalized into the ledger |
| Experimental provider telemetry | Documented Claude execution traces remain explicitly beta |
| Official quota payload | Optional adapter captures documented status-line fields; not live-provider validated here |
| Manual quota | UI/REST snapshots entered by a user; demo snapshots are clearly synthetic/manual |
| TraceQuota quota estimate | Uses explicit user-assumed capacity and stores its basis; not authoritative subscription usage |
| Experimental quota collection | Disabled interface; no scraping, credential access or undocumented network call implemented |
| Provider-emitted cost | Retained separately; Claude's emitted cost is itself an estimate |
| TraceQuota cost estimate | API-equivalent USD with dated pricing metadata; never a subscription bill |

Snapshots contain provider/account, capture time, source, optional session/task attribution, demo flag and named rolling/weekly/fixed windows. Used percentage is validated; remaining percentage is calculated. Snapshot identity is immutable: a conflicting reuse returns an error.

For a task, matching finds the latest eligible capture at/before start within 24 hours and first at/after completion within 15 minutes, with matching provider/account/demo and optional task/session attribution. Delta is **percentage points**. A changed reset time, reset between captures or decreasing usage gives an explicit reset crossing and null delta. Missing evidence stays missing. Account-wide quota changes may include concurrent sessions, so correlation is not causal task allocation. Capture tolerances and sparse evidence remain limitations.

Input, output, cache read and cache write stay separate. Generic inclusive input counts are adjusted when cache details are supplied; Claude's dedicated input count is already uncached. The pricing snapshot effective 2026-09-28 stores applied rates with each request. Unknown models, pre-snapshot observations and unsupported variants remain unpriced. A partly priced task exposes partial cost and an unpriced count, while its complete estimate remains null. Five-minute cache writes are a stated assumption; an annotated one-hour TTL uses the corresponding rate.

## Claude surfaces and configuration

Research used current upstream documentation, recorded in [current capabilities](research/current-capabilities.md). These instructions were checked against documentation, **not against an authenticated live Claude session**.

| Surface | Status |
|---|---|
| Claude Code CLI | Documented metrics/events adapter and optional beta traces implemented; live runtime pending |
| Claude Desktop Code → Local | Official Local environment configuration documented; live runtime pending |
| Generic agents | Standard OTLP accepted; protocol support does not prove every agent integration |
| Desktop ordinary Chat/Cowork | No automatic equivalent telemetry support claimed |
| Cloud/SSH execution | Their localhost is remote; requires a separately reachable collector, outside default V1 |
| Codex/Gemini/OpenCode/Cursor/frameworks | Provider-neutral design, dedicated adapters are roadmap work |

CLI essentials: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`. Optional beta traces add `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` and `OTEL_TRACES_EXPORTER=otlp`. Keep provider content logging disabled. Full shell and PowerShell examples are in [Claude onboarding](integrations/claude-code.md).

Desktop Local uses the environment dropdown's gear editor; shell variables may not be inherited. User settings can contain the documented env keys; repository settings cannot enable exporter destinations under current upstream rules. Restart the session after configuration. The optional status-line adapter uses host Python only when selected; it forwards safe fields from stdin to localhost and does not read credentials, poll Anthropic or generate model requests.

## Running on macOS, Linux and Windows

The repository is prepared for public distribution; its clone URL remains a placeholder until publication. In the repository directory:

```text
docker compose up -d
docker compose ps
docker compose run --rm tracequota-doctor
docker compose run --rm tracequota-demo
```

macOS: install/start Docker Desktop using Apple Silicon or Intel Linux containers. Linux: start Docker Engine with its Compose plugin. Windows 11: start Docker Desktop with WSL2 and Linux containers, then use the same commands in PowerShell. The core requires no host Python, Node, Make, bash or compiled companion. Named volumes and relative configuration mounts avoid machine-specific paths. Optional port overrides are in `.env.example`.

Open TraceQuota at `http://localhost:8080`, Grafana at `http://localhost:3000`, Phoenix at `http://localhost:6006`, Prometheus at `http://localhost:9090`. PostgreSQL remains internal. Grafana has anonymous Viewer access; its default local admin credentials are documented in the README and configurable. UIs/OTLP ports bind loopback.

Demo sends three projects, ten sessions, twenty tasks, sixty LLM requests, tool calls, multiple models, main/Explore agents, four token categories and forty quota snapshots. The default fixture date is twelve hours behind UTC now; a fixed `DEMO_DATE` reproduces identical IDs and values. Replays are idempotent. Every demo record is labeled synthetic. The generic fixture is separately labeled demo and can be sent with curl or PowerShell.

`docker compose down` preserves named volumes. `docker compose down -v` permanently deletes stored local data and is the explicit reset. Full acceptance is `python tools/acceptance.py` where host Python is available, or run its documented Compose steps individually. It checks service health, demo ingestion, Phoenix trace, Prometheus metrics, Grafana provisioning, duplicate replay and persistence after down/up.

## Security and privacy

No TraceQuota accounts, mandatory SaaS or application analytics. During operation, configured storage/exporters stay local. Dependency/image downloads and optional vulnerability/manifest checks use public registries. Prompts, responses, source contents, shell output, credentials and auth tokens are not stored by default. Hooks ignore transcript/prompt/cwd bodies. Metadata labels can still be sensitive; allowlisting is not a universal secret detector. Existing historical data is not erased by a later configuration change.

The API rejects writes with nonlocal browser origins. Nginx limits content/framing and request sizes. The API image runs as a nonroot user; Grafana gets a read-only database role. There are no Docker-socket mounts, privileged containers, host networking or automatic publication. This is a single-user local system; LAN/public deployment requires a separate authentication/security design. Rich capture is a reviewed deployment configuration change and must respect the final Phoenix sanitizer.

## Tests and observed results

| Check | Observed result |
|---|---|
| Backend suite on SQLite | 26 passed |
| Backend suite on disposable PostgreSQL 17 | 26 passed |
| Migrations and repeated upgrade | Passed on SQLite and native PostgreSQL |
| Ruff lint/format | Passed, including integrations |
| TypeScript and production Vite build | Passed |
| Frontend formatting/helper tests | Passed; 4 tests |
| npm dependency audit | 0 reported vulnerabilities |
| Python dependency audit | No known vulnerabilities reported |
| Compose configuration | Passed with installed Compose 5.5.1 |
| Collector 0.161.0 configuration/startup | Passed natively on Apple Silicon |
| Native Collector → API/PostgreSQL/Phoenix | Passed; related trace found through Phoenix GraphQL |
| Native synthetic ledger | 20 tasks, 60 requests, 3,207,000 total token activity; replays preserved counts |
| Native Collector/ledger metrics export | Passed; synthetic cache activity present |
| Native Prometheus scraping | 12 synthetic project/category series totaling 3,207,000; ledger cache-read series 2,406,570 |
| Native Grafana datasources | All 23 panels queried successfully through provisioned datasources; related PostgreSQL and Prometheus values verified |
| Native PostgreSQL restart persistence | Passed; tasks and quota remained after a server restart |
| Dashboard PostgreSQL queries | 66 passed: 22 SQL panels × all/demo/live |
| Browser verification | Overview, task modal, project totals, live/demo separation, successful manual snapshot saving and Grafana dashboard |
| Upstream image manifests | All eight pinned upstream images advertise linux/amd64 and linux/arm64 |
| Full Docker startup/smoke/volume restart | Pending: no engine available locally |
| Actual Claude CLI/Desktop integration | Pending: no authenticated provider execution performed |
| Hosted CI and cross-platform Docker builds | Workflows provided, not executed in this local unpublished repository |

Native smoke evidence is in [validation/native-smoke.json](validation/native-smoke.json), [Grafana query evidence](validation/grafana-query-evidence.json) and [full native stack evidence](validation/full-native-stack.json); screenshots are in [screenshots](screenshots). Native test services use temporary databases/runtime configuration, never user databases. The browser-created `ui-validation` snapshot was verified in the disposable database and then removed.

The native environment used Python 3.10.19 and Node 20.20.0; containers/CI target Python 3.12 and Node 24. Therefore native tests do not prove those container builds. A Starlette test-client deprecation warning remains, with no failed tests. Collector warns about two upstream deprecated aliases; both work with the pinned release, but should migrate with future upgrades. Local Phoenix package installation needed compatible eval/graphql dependency pins in its temporary test environment; this does not establish the health of the upstream Docker image.

## Remaining roadmap and unresolved technical risks

1. Run full Docker acceptance on Linux amd64, macOS Apple Silicon/Intel and Windows 11/WSL2; verify actual image builds, health probes, volume ownership and restart persistence. Provided workflows are coverage definitions, not successful CI evidence.
2. Validate sanitized real Claude fixtures and Local sessions across versions, including beta attribute availability and official status-line quota capture.
3. Complete container security scans and maintain upstream patch versions/digests; application dependency audits do not cover bundled container OS packages.
4. Add durable Collector queues and retention. A long outage or Collector restart can lose pending telemetry.
5. Improve request/interaction reconciliation when shared IDs are missing; limit ambiguity with concurrent sessions. Missing boundaries, metadata and quota remain visible.
6. Expand historically dated pricing and explicit variants; avoid assuming token usage equals subscription consumption.
7. Add pagination and scalable aggregates. UI/overview output is capped at recent 1,000 tasks; ingestion/request history is not a large-deployment analytics engine.
8. Improve quota freshness, multi-account mapping and overlap interpretation; reliable causal attribution is not established by before/after percentages.
9. Add validated trace deep links and dedicated future agent adapters. Instruction/diff efficiency analysis and a distributed companion are future features.

The implemented components and native evidence are reviewable now. A temporary native preview is available at `http://localhost:5173`, with Grafana/Phoenix/Prometheus on their normal ports. These test services use disposable native runtime configuration and are not the canonical deployment. Stop them before starting Compose on the same ports. The initial-complete claim remains withheld until the required Docker startup and container persistence path is demonstrably validated. Related Grafana metrics have been verified through the native runtime.
