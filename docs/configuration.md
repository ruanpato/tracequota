# Configuration, storage and updates

Defaults work without `.env`. Copy `.env.example` to `.env` in the repository root to override them. Environment files are ignored by Git and excluded from container builds. Never commit provider keys, tokens or database dumps.

## Compose settings

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_PASSWORD` | `tracequota-local` | Initial internal ledger password |
| `GRAFANA_PASSWORD` | `tracequota-local` | Initial Grafana administrator password; username `local` |
| `WEB_PORT` | `8080` | TraceQuota UI/API loopback ingress |
| `GRAFANA_PORT` | `3000` | Grafana loopback UI |
| `PHOENIX_PORT` | `6006` | Phoenix loopback UI |
| `PROMETHEUS_PORT` | `9090` | Prometheus loopback UI |
| `OTLP_GRPC_PORT` | `4317` | Host OTLP gRPC ingress |
| `OTLP_HTTP_PORT` | `4318` | Host OTLP HTTP ingress |
| `TRACEQUOTA_PRICING_SYNC` | `true` | Startup bundled-registry sync; set `false` only with an explicit sync workflow |

Overrides change host ports, not internal service names/ports. Displayed Grafana/Phoenix links follow their overrides. Update host exporters, hooks and status-line destinations when OTLP/web ports change. Restart with `docker compose up -d --wait --wait-timeout 300` after edits.

Default passwords are known localhost development values. Choose different first-start passwords if other local users are untrusted. Changing `.env` after initialization does **not** rotate PostgreSQL/Grafana credentials; rotate through those services and keep connection settings consistent. The internal `grafana_reader` role has SELECT-only permissions and the documented `local-readonly` password. PostgreSQL is not exposed to the host. LAN/Internet exposure needs a separately designed authentication/TLS/secrets setup and is outside this release.

## Development and tool variables

Compose supplies `DATABASE_URL`, `PYTHONPATH`, `GRAFANA_PUBLIC_URL` and `PHOENIX_PUBLIC_URL`. `PHOENIX_ENDPOINT` controls the sanitized trace relay in host development; the container default points to `phoenix:6006/v1/traces`. Tools accept `API_URL`, `OTLP_URL`, `PHOENIX_URL`, `PROMETHEUS_URL` and `GRAFANA_URL` for other test topologies. `DEMO_DATE=YYYY-MM-DD` pins synthetic identities; `TEST_DATABASE_URL` selects a disposable PostgreSQL test database. The optional Claude status-line script accepts `TRACEQUOTA_URL` to change its localhost snapshot destination. These are not required Quickstart settings.

## Persistent storage and backups

| Volume | Data |
|---|---|
| `postgres-data` | Ledger, quota, metric observations and pricing registry |
| `phoenix-data` | Sanitized trace database |
| `prometheus-data` | Time series |
| `grafana-data` | Grafana state |

Docker prefixes names with the Compose project. `down` preserves volumes; `down -v` permanently erases them. No retention job currently prunes the ledger.

Before updates, dump PostgreSQL inside its container and copy the binary file out. This avoids shell-specific binary redirection:

```bash
docker compose exec -T postgres pg_dump -U tracequota -d tracequota -Fc -f /tmp/tracequota-backup.dump
docker compose cp postgres:/tmp/tracequota-backup.dump ./tracequota-backup.dump
docker compose exec -T postgres rm /tmp/tracequota-backup.dump
```

Move the dump to private backup storage; `*.dump` is ignored by Git. This backs up the ledger only. Stop the stack and use your runtime's volume-backup workflow for Phoenix/Prometheus/Grafana. Restore-test backups before relying on them. Restore an older ledger only with a compatible application/schema; never overwrite a live database blindly.

## Updates

From a clean checkout, after backup/changelog review:

```bash
git pull --ff-only
docker compose up -d --build --wait --wait-timeout 300
docker compose run --rm tracequota-doctor
```

Builds use locked dependencies. API startup migrates and synchronizes bundled prices without repricing history. Rollback can require a matching database backup. TraceQuota application images are not published; `docker compose pull` alone cannot update API/web source.

## Pricing and client settings

Use Settings or the [pricing CLI](../pricing/README.md). Invalid catalogs fail before import. Status exposes bundled/database hashes and sync state. Change models/aliases/dimensions/dated rates through the [pricing contribution workflow](pricing/contributing.md).

Client examples are opt-in fragments to merge into existing host settings. Keep client identity separate from provider/billing platform, content logging disabled and unknown usage nullable. See [client guides](README.md#client-guides).
