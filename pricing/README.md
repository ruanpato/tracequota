# Bundled pricing registry

This Git-managed registry is authoritative for V1. It is data, not executable configuration. No per-request network lookup or mandatory central service exists.

`schema/pricing.schema.json` is generated from the strict Pydantic validator. `providers/*.json` contain currency, exact model IDs/aliases and declarative rules. Conditions specify billing platform, service tier, region, inclusive context bounds and optional cache write TTL. Effective dates begin at UTC midnight; timestamp boundaries must include a timezone. `effective_until` is exclusive. Prices are decimal strings. Rates describe metric, unit and whether missing telemetry prevents a complete estimate.

Each rule records an official source URL, title and checked date. Initial catalogs were checked 2026-09-28 against [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [OpenAI pricing](https://developers.openai.com/api/docs/pricing) and [Google pricing](https://ai.google.dev/gemini-api/docs/pricing). Their effective period starts at verification, not an invented historical release date.

Included text models: Claude Sonnet 4.6/5.5, Opus 4.6/5.5, Haiku 4.5; GPT-6 Astra/Sol/Luna and GPT-5.3 Codex; Gemini 2.5 Pro. OpenAI GPT-6 context thresholds and modifiers are also verified against each official model page. Coverage deliberately excludes other models, cloud reseller pricing, regional rates, multimodal rates and account-specific discounts. These remain unknown. Google cache storage uses measured token-hours; grounding allowances are not inferred. Rule notes identify excluded charges.

```sh
# Inside the existing Compose service, using its database configuration:
docker compose run --rm tracequota-api python -m tracequota pricing validate
docker compose run --rm tracequota-api python -m tracequota pricing sync
docker compose run --rm tracequota-api python -m tracequota pricing status
```

Settings → Pricing exposes the same local sync. API startup synchronizes bundled catalogs by default, prints CLI sync status, and fails visibly on invalid data. Set `TRACEQUOTA_PRICING_SYNC=false` to require explicit sync. Validation is fail-fast and imports are atomic and idempotent by canonical content SHA-256. Stored estimates are never recomputed by sync.

See [architecture](../docs/pricing/architecture.md), [contributing](../docs/pricing/contributing.md) and [catalog changelog](CHANGELOG.md).
