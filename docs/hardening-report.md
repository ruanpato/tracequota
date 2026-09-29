# Dependency, integration and interface follow-up — 2026-09-29

This follows the [initial publication record](release-readiness.md). The GitHub repository remains private. Documentation and source identifiers remain en-US; the interface now offers en-US and pt-BR.

## Implemented changes

- Refresh React/types 19.3.0, TypeScript 7.0.2, Vite 8.3.1, React plugin 6.1.1, Vitest 5.0.2 and Prettier 3.9.9; regenerate the npm lock and declare Node 24 or later.
- Refresh SQLAlchemy 2.1.1 and Python 3.14.7 containers; keep Pydantic's required `pydantic_core` pin rather than updating that internal package independently.
- Refresh Node 24.21.0 LTS, Nginx 1.31.5, PostgreSQL 17.11, Phoenix 20.16.0, Prometheus 3.15.0 and Grafana 13.2.3. The Collector was already current at 0.161.0. Workflow actions are updated to their current release lines.
- Group weekly dependency PRs, enable GitHub vulnerability alerts/security fixes and retain Node 24 LTS plus PostgreSQL 17 storage compatibility. Node 26 is not yet the selected LTS; PostgreSQL 18 needs an explicit data migration. These are documented compatibility decisions, not unreported vulnerable dependency exceptions.
- Add Cursor metadata hooks with loopback-only transport, no redirects/proxies, private-input filtering, prompt-safe failure behavior, generation/session separation and truthful capability labels. Native Cursor execution remains untested. No tokens, prices or quota are fabricated.
- Add an opt-in Claude Code/Codex user-settings helper with private backups and preserved unrelated/authentication settings. All machine-specific output remains in user settings or ignored artifacts, not documentation or screenshots. No provider login or model requests occur.
- Add lightweight en-US/pt-BR catalogs, persisted language selection, plural/interpolation handling and locale-aware numbers/dates while keeping USD and UTC semantics. API identifiers, provider metadata and user titles remain unchanged.
- Fix cost-card padding and wrapping, responsive columns/toolbars, translated long labels and prompt controls. Setup prompts follow the selected language and are offered only for implemented adapters.

## Validation

Measured locally on Linux arm64 containers with a macOS host:

| Check | Result |
|---|---|
| Backend SQLite | 89 passed on Python 3.14 |
| Backend PostgreSQL 17.11 | 89 passed against an isolated test database |
| Final client/privacy checks | 15 passed |
| Frontend | 8 passed; TypeScript lint, Prettier and production build passed |
| Dependency audit | npm: zero vulnerabilities and no outdated packages; pip-audit: no known vulnerabilities; pip check passed |
| GitHub Dependabot alerts | No open security alerts at validation time |
| Documentation | 40 Markdown files, 135 local links and 34 external URLs checked |
| Secret scan | Candidate source and existing Git history: no leaks |
| Updated containers | All seven services started; doctor checks passed |
| Synthetic end-to-end pipeline | Ledger, replay, pricing, quota, Phoenix, Collector metrics and 34 Grafana panels passed |
| Dashboard SQL | 99 queries across all/demo/live passed with the read-only role |
| Existing-volume persistence | Demo records survived dependency upgrades and service recreation |
| Browser layouts | en-US/pt-BR checked at 320, 390, 768 and 1280 CSS pixels; cost cards/rows contained their contents; mobile task details, settings, quota and setup prompts checked |

A new clean checkout with isolated volumes passed the documented build/start, doctor, synthetic smoke, browser access, shutdown/restart and persistence steps. Existing application volumes were preserved and restored afterward. [Hosted CI run](https://github.com/ruanpato/tracequota/actions/runs/36563922866) passed all eight jobs: Linux/macOS/Windows portable checks, PostgreSQL, Compose acceptance, API/web amd64+arm64 builds and dependency/security scanning. All 17 original Dependabot PRs are closed as superseded; their supported updates are consolidated in commit `899db2a`, with Node 26/PostgreSQL 18 deferred under the documented compatibility policies. GitHub reports no open vulnerability alerts.

Local Claude Code/Codex telemetry settings were parsed and checked for loopback endpoints and disabled content capture; private backups stay in user directories. Installed Cursor was detected, while native hook execution is still untested. New client sessions and ordinary user work are required to verify real telemetry; no model request was made to produce validation data.

 Starlette currently emits one upstream TestClient deprecation warning for its supported `httpx` compatibility path; tests pass and the pinned package is current. It is not suppressed. Phoenix's newly introduced assistant/MCP features are disabled; only trace ingestion/inspection is used.
 Native model execution is deliberately excluded: configured settings are not proof of observed provider telemetry. Screenshots contain synthetic data only.
