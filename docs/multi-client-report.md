# TraceQuota 0.2 — multi-client architecture and versioned pricing

Implementation date: 2026-09-28. Native validation finished overnight in UTC on 2026-09-29. This report supersedes the architecture and pricing portions of the [initial V1 report](implementation-report.md), which remains a historical record.

The existing application now separates execution clients from model providers, supports mixed-provider tasks, and prices new model calls through an immutable, Git-managed registry. The local native stack passed its end-to-end checks. Docker Compose configuration validates, but Docker builds, container health and volume restart acceptance remain **unverified** because no Docker engine is running on this machine. No authenticated native client sessions or real provider requests were used.

## Changes and preserved architecture

The pre-change audit and migration plan were written before editing application code: [migration strategy](migrations/multi-client-pricing.md). The implementation extends the existing FastAPI/SQLAlchemy/Alembic backend and React/TypeScript frontend. It preserves the seven main Compose services: PostgreSQL, API, web, OpenTelemetry Collector, Phoenix, Prometheus and Grafana. The four existing named volumes, optional tool profile, host OTLP endpoints, local privacy boundaries and independent quota ledger remain.

Existing routes, task lifecycle, Claude hooks/status-line adapter, generic OTLP ingestion, provider-emitted costs, legacy token display fields, original 20-task demo and Grafana panels remain available. New code does not proxy model traffic, fetch credentials, scrape quota pages or introduce a mandatory remote pricing service. The Python domain/telemetry implementation still ships inside the API; separate distribution packages remain documented interfaces.

The new implementation lives primarily in `clients.py`, `usage.py`, `pricing.py`, `analytics.py`, the existing telemetry/ingestion modules, `pricing/`, frontend screens and the existing Grafana dashboard. The API and UI identify themselves as version 0.2.0.

## Database migrations and preservation

| Migration | Additive changes |
|---|---|
| `0003_multi_client_pricing` | Indexed task client identity; event client/provider/model/pricing-rule identity; nullable safe raw and normalized attribute columns; execution sessions, agent runs, immutable catalog versions and pricing rules |
| `0004_multi_client_analytics` | Extends the existing PostgreSQL `request_usage` view with client/surface/runtime/integration/platform/repository, canonical usage, rule/hash/confidence, partial cost and component fields; uses each call's provider |

PostgreSQL uses JSONB for the two new attribute columns; SQLite uses JSON. Model calls remain events in the established ledger. Workspace/project/repository metadata stays associated with execution entities rather than requiring an incompatible table rewrite. Legacy sessions still appear through task aggregation even when no new session entity exists.

Backfill identifies clients only from explicit or recognizable client metadata. An Anthropic provider value alone does not become Claude Code. Existing event payloads, estimates, quota records and metric observations are preserved by migration. On the native PostgreSQL ledger, all **120 original event payloads were exactly equal immediately after upgrade**, with 20 tasks, 40 quota snapshots and 88 metric observations unchanged. After demo replay, all original event IDs and pricing payloads remained; provider-emitted monetary amounts retained the same Decimal value, with replay capable of upgrading numeric representation to a decimal string and enriching metadata.

New request identity includes workspace, client and demo/live identity alongside the legacy stable request identity. Compatible legacy IDs are recognized on replay. Different clients with the same provider/session/request ID remain separate. Catalog synchronization and replay never recalculate stored historical estimates. Migration preservation and replay are covered by regression tests.

Span replay also checks trace/span identity within compatible client/workspace/session boundaries, so enriching client metadata cannot duplicate a previously stored span. The native test ledger retains 60 additional nonbillable metadata spans created during an earlier testing iteration, before this protection was added; they were not purged. Its 210 event rows still contain exactly 75 model calls, with unchanged original pricing and no duplicate model charges.

## Execution domain and supported clients

The graph is workspace → project/repository and execution session → task → agent run → model call/tool/MCP/other event. Each call retains client/version, surface, runtime, integration type, provider, billing platform, requested/resolved model, service tier, region and available context. Parent agent and trace/span identities preserve execution relationships. A single OpenClaw task may call both OpenAI and Anthropic.

Provider/account quota snapshots remain independent of execution identity. Task details return quota evidence for every relevant provider while retaining legacy primary-provider fields. Quota deltas use percentage points with reset detection and explicit missing evidence. An account-wide change can include concurrent work; it is not a causal allocation of quota to one task.

| Client | Integration descriptor | Model calls / tokens / tools | Cache / reasoning | Agents | Quota | Validation |
|---|---|---|---|---|---|---|
| Claude Code | `native_otel` | Partial | Provider dependent | Partial | Partial: optional documented status-line adapter | Untested native session |
| Codex | `native_otel` | Partial | Provider dependent | Partial | Unsupported official retrieval | Untested native session |
| OpenClaw | `plugin_otel` | Provider dependent | Provider dependent | Partial | Unsupported official retrieval | Untested native session |
| Gemini CLI | `native_otel` | Partial | Provider dependent | Partial | Unsupported official retrieval | Untested native session |
| GitHub Copilot CLI | `tracequota_adapter` | Experimental | Provider dependent, unvalidated | Partial contract, unvalidated | Unsupported | Planned; no adapter shipped |
| OpenCode | `plugin_otel` | Experimental | Provider dependent, unvalidated | Partial contract, unvalidated | Unsupported | Planned; no plugin shipped |
| Generic OTLP | `tracequota_adapter` | Partial | Provider dependent | Partial | Unsupported official retrieval | Synthetic contract tested |

Descriptors explain the integration boundary; they do not establish that a client is connected. Demo traffic never establishes a live `last_seen`. Content capture is unsupported throughout the default configuration. The current normalizer shares a conservative OTLP contract with documented Claude handling and selected Codex/Gemini token keys; it is not a complete, live-certified adapter for every upstream version.

Client guides: [Claude Code](integrations/claude-code.md), [Codex](integrations/codex.md), [OpenClaw](integrations/openclaw.md), [Gemini CLI](integrations/gemini-cli.md), [Copilot CLI](integrations/copilot-cli.md), [OpenCode](integrations/opencode.md). They distinguish official upstream export features from TraceQuota validation. OpenClaw's upstream exporter requires its official diagnostics OTel plugin. Ordinary desktop chat and remote environments do not inherit local CLI support automatically.

## Pricing registry and JSON structure

The bundled registry contains **3 providers, 10 canonical models and 43 rules**, schema version 1, catalog version `2026.09.28.1`. Its canonical content hash is:

```text
ece649c7e23a372f93478ec6632560aacff82426ac16f6df274a100d15031e82
```

The [JSON Schema](../pricing/schema/pricing.schema.json) is generated from the strict Pydantic models. Each provider JSON contains `schema_version`, `version`, `provider`, USD `currency`, exact model IDs/aliases, and rules. Rules contain an ID, model ID, effective interval, dimension conditions, metric/unit/rate/required components, reasoning policy, official source metadata and notes. Unknown fields and invalid values fail validation. Rates are decimal strings, not executable expressions.

For example, an Anthropic Sonnet 4.6 rule combines direct Anthropic billing, standard tier, global region and five-minute cache TTL with these rates per million tokens:

```json
{
  "input_uncached": "3",
  "output_total": "15",
  "cache_read": "0.3",
  "cache_write": "3.75"
}
```

This is a compact illustration of rate data; the actual catalog stores each component as a metric/unit/rate/required object alongside its conditions and provenance. The full [Anthropic](../pricing/providers/anthropic.json), [OpenAI](../pricing/providers/openai.json) and [Google](../pricing/providers/google.json) files are the source of truth.

| Provider catalog | Models | Initial pricing dimensions |
|---|---|---|
| Anthropic | Sonnet 4.6/5.5, Opus 4.6/5.5, Haiku 4.5 | Standard direct API; five-minute/one-hour cache writes |
| OpenAI | GPT-6 Sol/Astra/Luna, GPT-5.3 Codex | GPT-6 standard/batch/flex/fast, short/long context; Codex standard |
| Google | Gemini 2.5 Pro | Standard/batch/flex/priority, short/long context; measured cache token-hours |

Rates were checked on 2026-09-28 against [official Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [official OpenAI pricing](https://developers.openai.com/api/docs/pricing) and [official Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), with GPT-6 context/tier details cross-checked on official model pages. The first effective date is the verification date. No earlier historical prices or unsupported model variants are invented. Bundled aliases are deliberately empty; the engine supports explicit exact aliases and tests them without fuzzy or prefix matching.

## Synchronization and historical strategy

`python -m tracequota pricing validate`, `sync` and `status` provide the local CLI. Settings offers status and bundled synchronization. Startup synchronizes by default; `TRACEQUOTA_PRICING_SYNC=false` requires manual sync. Container startup keeps migration and pricing synchronization in the existing API service.

Synchronization validates all files before writing, canonicalizes content and computes SHA-256, then atomically imports immutable versions/rules and activates one hash under the existing transaction lock. Reimporting identical content creates no duplicate rules; it updates the last-sync timestamp. Invalid or overlapping rules fail visibly. JSON formatting or object-key order does not create a new version.

Rules select against each call's timestamp. UTC dates and timezone-aware timestamps are supported; end boundaries are exclusive. Context bounds, platform, tier, region and TTL constrain matching. Gaps and unsupported dimensions remain unknown. Catalog changes apply only to newly ingested calls, including newly arriving older calls if a historical rule exists. Already stored estimates remain frozen, even when replay follows a catalog update. Legacy pricing payloads retain their original version/rates and are labeled `legacy` in analytics.

V1 CLI/API synchronization reads bundled files only. A local-root loader supports tests and future extensions; user overrides, remote registries, signatures and precedence policies are future work. See [pricing architecture](pricing/architecture.md), [contributing](pricing/contributing.md) and [catalog changelog](../pricing/CHANGELOG.md).

## Usage, cache and monetary semantics

Canonical quantities are nullable `input_total`, `input_uncached`, `cache_read`, `cache_write`, `output_total` and `reasoning`. Each carries source-key and normalization/semantic provenance. Known zero differs from missing. Legacy four-bucket token fields remain as known-activity compatibility displays; they cannot prove that an unknown bucket was zero.

Dedicated Claude Code `input_tokens` is treated as uncached. Generic input is reduced by cache only when explicitly inclusive and both cache quantities are known; negative results are rejected as unusable. Unknown semantics do not trigger subtraction. Exclusive-reasoning output is normalized to inclusive output; inclusive reasoning is charged once. A separate-reasoning rule subtracts reasoning from ordinary output before charging a separate component.

All new monetary calculations use Decimal and persist decimal-string quantities, rates, subtotals and totals. Required unknown usage makes the complete total null while retaining the known priced subtotal. Positive usage with no corresponding rate is reported as partial. Missing cache TTL with positive writes leaves that component unknown; it does not silently charge five-minute writes. Known zero writes can still permit a complete token estimate. Unsupported model, platform, tier, region or effective period produces visible unknown pricing.

Every new estimate freezes rule ID, catalog hash/version, source, timestamp applicability, conditions, component breakdown, confidence, assumptions, warnings and notes. Missing platform/tier/region may use explicit recorded direct/standard/global assumptions. Confidence is `exact`, `high` for an exact alias, `estimated`, `partial` or `unknown`; an exact rule match still describes an **estimated API-equivalent workload**, not an actual invoice.

Three monetary concepts remain separate: provider-emitted observed cost, TraceQuota API-equivalent estimate, and actual subscription charge/incremental bill. The last remains unknown. Quota is not converted into a subscription price. Cache storage is billed only when measured token-hours are supplied; grounding, multimodal usage, free allowances, discounts, taxes, tool charges and cloud reseller prices need their own evidence/rules. A complete token estimate does not imply a complete invoice.

## UI, analytics and Grafana

The UI adds independent filters for client, surface, runtime, integration type, provider, billing platform, model, project, repository, agent, pricing confidence and dates. Overview shows estimated API-equivalent today/week/month, incomplete call counts, cost by client/provider/model/project/agent and usage coverage. Missing costs render as Unknown. Empty or incomplete evidence is not disguised as zero cost.

Sessions and task rows show execution client and multiple providers. Task detail displays model-call pricing provenance/components and per-provider quota evidence. Settings displays the bundled/active hash, provider/model/rule counts, last sync and synchronization result. Integration cards show actual validation states. The quota form accepts a provider independently from account and evidence source.

Client/provider filters scope both costs and token activity to the selected model calls. The mixed OpenClaw example verifies that filtering OpenAI excludes its Anthropic call. Full-ledger overview/session/project/metric aggregation is independent from the existing 1,000-row task-list cap. Grouping remains in memory in V1.

All original 23 Grafana panels remain. Eleven panels add client/provider/model token activity, client/provider/agent API cost, cost over time, pricing confidence, unknown model calls and cache cost components, bringing the dashboard to **34 panels**. Existing request-usage panels gain client/provider/model/project/agent variables. Separate quota evidence panels retain provider/account semantics rather than pretending quota is client-specific. New cost panels expose known partial costs and missing pricing.

Verified screenshots: [desktop overview](screenshots/multi-client-preview.png), [mobile overview](screenshots/multi-client-mobile-preview.png), [mixed-provider investigation](screenshots/mixed-provider-task.png), [pricing settings](screenshots/pricing-registry.png).

## Added tests and results

Pricing tests cover manually calculated Anthropic costs, one-token Decimal precision, both cache TTLs and missing TTL, inclusive/uncached input, reasoning inclusion/separate billing, missing usage, non-token units, OpenAI tiers/context, Google context/storage, exact aliases, unsupported dimensions/models, effective-date gaps and intraday transitions, malformed schemas, negative/non-finite rates, overlapping rules, content hashes, atomic imports and idempotence. Domain/API regressions cover mixed-provider costs/quotas, filters, privacy allowlist agreement, client identity collisions, historical freeze/replay, safe migration and aggregation beyond 1,000 tasks.

| Verification | Observed result |
|---|---|
| Backend suite, SQLite | 77 passed |
| Backend suite, native PostgreSQL | 77 passed |
| Final replay/descriptor regressions | Included in both passing full suites |
| Frontend suite | 4 passed |
| Frontend production build, lint and formatting | Passed |
| Python lint | Passed |
| Python/npm dependency audits | Zero known vulnerabilities reported at check time |
| Bundled catalog validation and repeated sync | Passed; immutable hash, no duplicate import |
| Additive migration on populated ledger | 120 original event payloads preserved before replay; stored pricing preserved after replay |
| Dashboard PostgreSQL SQL | 99 queries passed across all/demo/live modes |
| Actual Grafana datasource execution | All 34 panels queried successfully |
| Native OTLP → Collector → ledger/Phoenix | Passed, including the mixed-provider trace |
| Prometheus mixed client/provider series | Positive cache-read series observed |
| Native PostgreSQL restart | Tasks, quota and mixed-provider history persisted; persistence tool passed |
| Browser desktop/mobile, filters, task investigation, settings sync | Passed |
| Docker Compose configuration | Passed |
| Docker build/container/volume acceptance | Unverified; no running engine |

The backend currently emits one upstream Starlette/httpx deprecation warning in the test harness. It does not fail the suite. Cross-platform CI and Compose acceptance workflows remain in the repository, but this local run does not establish that every CI job or operating system passed.

The combined synthetic ledger contains **25 tasks, 15 sessions, 75 model calls and 52 quota snapshots**, retaining the original Claude demo while adding Codex, OpenClaw and Gemini examples. The mixed task's complete cost equals its model-call sum; independent filtered client/provider totals and two-provider quota evidence pass assertions. No synthetic values are presented as real account evidence. Machine-readable evidence is in [native validation](validation/multi-client-native.json).

## Evidence classifications and remaining limits

| Classification | Meaning in this implementation |
|---|---|
| **Official** | Pricing and client export documentation come from primary upstream sources; the optional Claude quota adapter reads a documented payload. Official provenance does not establish a live integration test. |
| **Measured** | Local HTTP health, database counts/persistence, test execution, Phoenix trace retrieval, Prometheus series and Grafana queries were observed. Demo token/quota quantities are synthetic inputs. |
| **Derived** | Canonical totals, cache-adjusted quantities with known semantics, remaining percentages and reset-aware quota deltas follow recorded inputs. |
| **Estimated** | Public API-equivalent workload values, default pricing assumptions and explicitly user-entered capacity estimates. |
| **Experimental** | Upstream beta traces, planned Copilot/OpenCode extension boundaries and any version-dependent native client semantics pending validation. |
| **Unsupported** | Automatic official quota retrieval outside the documented Claude adapter, default content capture, ordinary desktop chat equivalence, unsupported models/platforms/regions/modalities and authoritative subscription invoices. |

Native verification used macOS Apple Silicon, PostgreSQL 17.11, Python 3.10, Node 20, Collector 0.161.0, Phoenix 13.15.0, Prometheus 3.5.0 and Grafana 12.3.0. This does not certify the Docker target runtimes or Windows/Linux host setup. No Docker Desktop application, reachable engine socket or alternate running Docker runtime was found. Installing a runtime was outside this implementation; the preserved Compose deployment still needs that acceptance run.

Native upstream export payloads may omit provider, cache, reasoning, service tier or billing platform. They remain partial/unknown unless supplied with valid semantics. Per-client golden captures from authenticated real sessions are still needed. Catalog coverage is intentionally finite and current from its verification date; no guessed historical rates or model families are used. Late duplicate metadata is merged while frozen pricing stays unchanged. Very large ledgers need SQL aggregation/pagination work. No repository publication, image publication or external deployment was performed.

## Next integrations

1. Validate authenticated Claude Code and Codex sessions end to end using privacy-safe golden payloads; document version/surface-specific fields and complete usage semantics.
2. Validate the OpenClaw diagnostics plugin with mixed providers and Gemini CLI's native log keys, including cache/reasoning mapping and correlation identifiers.
3. Run the existing Docker acceptance suite and volume restart checks when an engine is available; then exercise the declared host platforms.
4. Implement and test actual OpenCode/Copilot adapters before changing their planned labels. Add official provider/account quota sources only when supported payloads exist.
5. Extend pricing coverage through reviewed official-source catalog changes; add cloud billing platforms, modalities and measured non-token components explicitly rather than matching them to direct text API prices.
