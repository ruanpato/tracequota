# Contributing

Start with an issue describing the problem and expected behavior. Focused pull requests are welcome. All project content uses English (en-US), including identifiers, comments, CLI/UI messages, examples and docs. No i18n framework is required. Preserve privacy defaults and keep provider-specific behavior behind adapters.

Contributions use the repository's [Apache-2.0 license](LICENSE). Preserve [NOTICE](NOTICE) and attribution; use compatible dependencies and do not copy undocumented provider integrations. Read the [development guide](docs/development.md) and [code of conduct](CODE_OF_CONDUCT.md).

## Run checks

With Docker running, from the repository root:

```bash
docker compose up -d --build --wait --wait-timeout 300
docker compose run --rm --build tracequota-test
docker compose run --rm tracequota-test python -m ruff check apps/api examples tools tests
docker compose run --rm tracequota-test python -m ruff format --check apps/api examples tools tests
docker compose run --rm tracequota-api python -m tracequota pricing validate
docker compose run --rm tracequota-doctor
docker compose run --rm tracequota-smoke
```

Rebuild test images after source changes. Container checks inspect image files rather than editing host sources. The development guide includes Python 3.12/Node.js 24 setup, frontend checks and full persistence acceptance. Tests use disposable databases; never configure the PostgreSQL test suite against real data.

## Models, providers, clients and pricing

- Model/rate additions usually require reviewed JSON catalogs, official sources, explicit effective periods and manually computed examples. Follow [pricing contributions](docs/pricing/contributing.md).
- Providers need separate model-service/billing-platform identity and independent sourced quota evidence.
- Clients need descriptors, safe normalization fixtures, nullable canonical usage, version/surface notes and onboarding. Label planned, experimental, partial and untested work accurately.
- Schema changes need additive Alembic migrations and history-preservation tests.
- Quota tests cover resets, missing windows, sources and concurrent-work attribution; an account-wide change is not causal task allocation.

Before a PR, run documentation validation, secret scans, builds, tests, lint/format and dependency checks. Do not commit environment files, databases, dumps, credentials, private traces, logs or generated builds. API/web images are built but not automatically published. Report vulnerabilities through [SECURITY.md](SECURITY.md), not public issues containing sensitive payloads.
