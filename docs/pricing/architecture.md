# Pricing and execution architecture

## Identity and hierarchy

A **client** executes work: Claude Code, Codex, OpenClaw or another coding tool. A **surface** locates that client (CLI, desktop, gateway); a **runtime** identifies its harness. An **integration type** explains how telemetry arrived. A **provider** serves the model; a **billing platform** invoices the workload. OpenClaw can call both OpenAI and Anthropic in one task. Neither provider implies a client. Billing platform IDs in the initial catalogs are `anthropic`, `openai`, and `google` for their respective direct APIs; an explicit `aws_bedrock`, `azure_openai` or other platform has no fallback rule.

Workspace → project/repository and execution session → task → agent run → model/tool/MCP/other event form the canonical graph. `execution_sessions` and `agent_runs` persist explicit execution entities; events remain the model-call ledger and preserve parent trace/span IDs. A known explicit task ID must match its client/session. API session lists also aggregate legacy tasks whose session entity was not recorded. Sessions group by workspace/client/session, never provider alone.

Supported namespaces include `tracequota.client.name` / `.id`, `.version`, `.surface`, `tracequota.runtime.name`, `tracequota.integration.type`, `tracequota.workspace`, `tracequota.task.id`, `tracequota.billing_platform`, `tracequota.service_tier`, `tracequota.region`, and `tracequota.context_tokens`. Earlier short aliases are accepted. GenAI provider, requested/resolved model, operation and conversation IDs are retained. Resolved model wins for pricing; requested model remains inspectable.

## Usage semantics

Canonical usage holds nullable `input_total`, `input_uncached`, `cache_read`, `cache_write`, `output_total`, and `reasoning`. Source keys, input/output semantics, normalizer/version and warnings accompany it. Missing is not zero. The deprecated four-category `tokens` fields show only known activity and remain for existing API consumers; consult `usage` coverage when interpreting totals.

Claude Code's documented dedicated `input_tokens` is uncached. Generic counters require explicit `tracequota.usage.input_semantics=inclusive|uncached` or separately supplied canonical `tracequota.usage.input_uncached`. Inclusive input is reduced only when all cache quantities are available and the result is nonnegative. Cache buckets never get subtracted from dedicated Claude input. Reasoning-inclusive output is billed once. `exclusive_reasoning` output is first normalized into an inclusive total; a separate-reasoning rule subtracts reasoning from ordinary output before pricing it separately. Unknown output semantics with measured reasoning produce partial pricing.

The default detector recognizes explicit client attributes and documented client/service names. All clients use a conservative shared normalization contract with client-specific documented Claude handling. Codex completion events can supply native token keys; incomplete native metadata stays partial. This is an extension point, not a claim that every upstream version has been tested.

## Three different monetary concepts

`observed_provider_cost` is emitted telemetry evidence, which may itself be a provider estimate. `estimated_api_equivalent_cost` is the Decimal value of a measured workload under public API rules. Subscription charges and incremental subscription bills are unknown; neither number is a subscription invoice. Quota is independent provider/account evidence and is never converted into authoritative money or inferred from tokens.

## Catalog, calculation and history

Git JSON catalogs validate through strict Pydantic models and a checked-in JSON Schema. Conditions are constrained equality fields and context bounds. No `eval`, expressions, executable plugins or remote price fetches exist. Model matching is exact canonical ID or an explicitly declared alias. Rules select by call timestamp, provider/model, platform, tier, region, context and TTL. Unknown platform/tier/region conditions fail rather than select direct pricing. Missing platform/tier/region can use clearly recorded direct/standard/global assumptions.

All monetary arithmetic uses Decimal. Each event freezes decimal-string component quantity/rate/subtotal, complete total (nullable), priced partial total, currency, rule ID, content hash, optional semantic catalog version, source, confidence, assumptions and warnings. Confidence is exact, high (exact alias), estimated (default assumptions), partial (missing/unpriced usage), or unknown (no usable rule/components). Existing estimates without this provenance retain their historical payload and are labeled legacy.

Imports validate the complete registry before writing, use the ingestion transaction/advisory lock, retain prior catalog versions/rules, and activate one immutable hash. Reimporting content updates last-sync time without duplicate rules. Sync changes only pricing for future ingestion; a late duplicate span never reprices its stored event. The loader accepts a local root for tests/future local registries, but V1 CLI/API use bundled files. Future overrides/signed registries need explicit precedence and trust policy.

## Analytics and limits

Task costs are sums of model calls; any incomplete call makes the complete sum unknown, with known components reported separately. The same filtered call set drives client/provider/model/project/agent cost attribution, so selecting OpenClaw/OpenAI excludes its Anthropic calls. Date filters use call time, including calls inside tasks begun earlier. Multi-provider task details expose one quota evidence group per provider/account; legacy primary-provider quota fields remain.

Safe raw attributes and normalized attributes use PostgreSQL JSONB columns, with JSON variants for SQLite. Collector, ledger and Phoenix enforce the same allowlist, stripping prompts, responses, scope/link content and arbitrary log bodies. Unlisted metadata is deliberately excluded to preserve privacy.

Current rates cover text tokens only, known cache storage where supplied, and a constrained mechanism for other per-request/second/token-hour rates. Unmeasured charges and modalities cannot yield an actual invoice. Registry notes disclose coverage. Native client export versions, account-specific bills, cloud reseller prices and official quota collectors require separate validation/work.

Task lists retain the existing 1,000-row response cap. Overview/session/project aggregates and metrics read the full ledger instead of truncating sums at that cap. V1 performs local in-memory grouping; large-ledger SQL aggregation and pagination remain future performance work.
