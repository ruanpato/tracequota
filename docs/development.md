# Development and validation

Use the [Quickstart](quickstart.md) for installation. Contributors use English (en-US) for source, comments, messages, examples and documentation. No i18n framework is required. Use the existing explicit date/number formatting boundary rather than browser defaults.

## Container checks

With a running engine, from the repository root:

```bash
docker compose up -d --build --wait --wait-timeout 300
docker compose run --rm --build tracequota-test
docker compose run --rm tracequota-test python -m ruff check apps/api examples tools tests
docker compose run --rm tracequota-test python -m ruff format --check apps/api examples tools tests
docker compose run --rm tracequota-api python -m tracequota pricing validate
docker compose run --rm tracequota-doctor
docker compose run --rm tracequota-smoke
```

These inspect image files; rebuild after changes. Format checks do not edit host sources. For frontend checks without host Node.js:

```bash
docker run --rm -v "${PWD}/apps/web:/app" -w /app node:24.14.0-alpine npm ci
docker run --rm -v "${PWD}/apps/web:/app" -w /app node:24.14.0-alpine npm test
docker run --rm -v "${PWD}/apps/web:/app" -w /app node:24.14.0-alpine npm run lint
docker run --rm -v "${PWD}/apps/web:/app" -w /app node:24.14.0-alpine npm run build
docker run --rm -v "${PWD}/apps/web:/app" -w /app node:24.14.0-alpine npm run format:check
```

Mount commands work in Unix shells and PowerShell; the runtime must permit the checkout mount. Optional host Python can run `python tools/acceptance.py` to orchestrate config, build/start, smoke and down/up persistence. Individual Quickstart commands require no host Python.

## Optional host setup

Use Python 3.12 and Node.js 24. On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check apps/api examples tools tests
.venv/bin/python -m ruff format --check apps/api examples tools tests
```

PowerShell uses `python -m venv .venv` and `.venv\Scripts\python.exe` thereafter; activation is optional. Tests default to temporary SQLite. `TEST_DATABASE_URL` selects a **disposable** PostgreSQL test database whose tables are created/dropped; never point it at application or production data.

For a local API, apply migrations and run Uvicorn. Unix shell:

```bash
export DATABASE_URL=sqlite:///./tracequota.db
.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head
PYTHONPATH=apps/api .venv/bin/python -m uvicorn tracequota.main:app --host 127.0.0.1 --port 8000
```

PowerShell sets `$env:DATABASE_URL = "sqlite:///./tracequota.db"` and `$env:PYTHONPATH = "apps/api"` before equivalent commands. PostgreSQL-only Grafana views and the full OTLP topology require the normal stack.

In another terminal, run `cd apps/web`, `npm ci` and `npm run dev`. Vite listens on localhost:5173 and proxies to API port 8000. Run `npm test`, `npm run lint`, `npm run build` and `npm run format:check`. `npm run format` and `ruff format` edit sources. Dependencies, databases and build outputs are ignored.

## Documentation, secrets and dependencies

```bash
python3 tools/check_docs.py
gitleaks dir --redact --no-banner .
gitleaks git --redact --no-banner .
```

The documentation checker verifies relative links/headings; `--external` adds network checks. Scan a clean staged export before publication to exclude ignored dependencies/auth files. Gitleaks is optional for developers, not a backend dependency. Redact logs and never publish credential snippets. Audit Python with `pip-audit -r apps/api/requirements.lock` and npm with `npm audit --audit-level=moderate`.

## Contribution boundaries

Schema changes require additive migrations and preservation tests. Follow [pricing contributions](pricing/contributing.md). Clients/providers need documented semantics, safe fixtures, honest capabilities and onboarding; synthetic success is not live certification. Quota tests include resets, missing evidence and concurrent-work attribution. Preserve history and privacy defaults. See [architecture](../ARCHITECTURE.md).

CI includes portable backend/frontend checks, PostgreSQL, Compose acceptance and amd64/arm64 builds. The manual desktop workflow needs actual self-hosted macOS/Windows runners and host Python. Local checks do not certify those environments.
