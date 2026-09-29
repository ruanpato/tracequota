# Multi-client and pricing migration

Inspected 2026-09-28 before implementation: the existing FastAPI/SQLAlchemy ledger has tasks, immutable request events, quota snapshots and separate metric observations. Alembic owns the schema; the Collector sanitizes telemetry before the ledger and Phoenix. PostgreSQL views supply Grafana, Prometheus exposes measurements, and React supplies seven local pages. The existing seven-service Compose stack and volumes remain authoritative.

## Assumptions being removed

The old normalizer inferred Anthropic from a generic input token attribute, grouped tasks by provider/session, and inferred Claude surface from Anthropic. Generic prompt totals lost cached quantities without explicit semantics. A Python rate table priced model prefixes, stored float estimates and could not distinguish client, platform, tier, context or historical rules.

## Additive design

Client, surface, runtime and integration type describe execution; provider, billing platform and resolved model describe a model call. Sessions and agent runs are explicit ledger entities. A task can contain multiple providers. Request events remain the authoritative call ledger and retain their original IDs. Safe source attributes and canonical normalized attributes are stored together. Missing usage is nullable; cache subtraction requires declared or documented semantics.

Git-managed JSON catalogs use a constrained declarative schema. Imports validate all files before an atomic, content-addressed database sync. New calls freeze Decimal component estimates with rule/catalog references. Sync never reprices existing events. Quota remains provider/account evidence, independent of client identity.

## Backward compatibility and migration

Migration adds indexed dimensions and catalog/session/agent tables; it does not drop telemetry or modify stored pricing JSON. Claude identity is backfilled only from explicit client metadata or documented Claude event/service signals. Provider alone is insufficient. Other old records become unknown. Legacy totals and endpoint fields remain available; new canonical usage and authoritative Decimal strings accompany them. Request IDs continue deduplicating old telemetry. Unknown costs are null and priced partial totals are separately reported.

## Risks and validation

Historical telemetry may not expose cache semantics, platform, tier or parent agents. These fields remain unknown rather than fabricated. Native client integrations require independent real-client testing; synthetic examples validate ingestion only. Catalog effective dates begin at verification when historical dates are unavailable. Validation covers overlap, aliases, missing dimensions, frozen historical estimates, preservation of existing Claude data, mixed-provider attribution and privacy across Collector/API/Phoenix. Compose acceptance requires a running container engine; native stack verification cannot prove Docker image builds.
