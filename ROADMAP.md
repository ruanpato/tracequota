# Roadmap

- Finish measured Docker Desktop acceptance on macOS Apple Silicon and Windows 11/WSL2; publish CI evidence for Linux and multiarch builds.
- Validate real Claude CLI and Desktop Local sessions across versions; add captured **sanitized** official fixtures.
- Resolve logs/spans without shared request IDs; improve interaction identity reconciliation and late/out-of-order metadata.
- Add durable Collector queues, retention, pagination and scalable SQL aggregates beyond V1's bounded views.
- Expand reviewed historical catalog coverage, additional models/providers, cloud billing platforms, regional rates and non-token charges. Existing catalogs already cover explicit cache TTL and selected processing/context tiers.
- Improve quota capture freshness and bracketing; show capture uncertainty and overlapping tasks without causal claims.
- Add verified Phoenix trace deep links per upstream release.
- Validate native Cursor hooks and obtain documented measured usage support if upstream provides it.
- Validate native Codex, Gemini CLI and OpenClaw mappings with safe real-client fixtures; implement the planned OpenCode/Copilot adapters while keeping OTLP generic.
- Expand translation coverage beyond the implemented en-US/pt-BR catalogs and improve accessibility in a separately scoped pass.
- Optional statically distributed host companion for doctor/configuration/manual task workflows.
- Optional instruction-change and diff-size correlation, anomaly detection and repository efficiency comparisons.

No gateway, proxy, orchestrator, enterprise auth, hosted service or Kubernetes platform is planned for V1.
