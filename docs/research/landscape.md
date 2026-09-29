# Open-source landscape — 2026-09-28

| Project | Documented focus | TraceQuota distinction |
|---|---|---|
| [ccusage](https://github.com/ccusage/ccusage) | Local usage/cost analysis from agent data | Shared OTLP pipeline and persistent task/quota ledger |
| [Quota Monitor](https://github.com/timmyagentic/quota-monitor) | Native macOS quota and session insights | Cross-platform container backend, no native app requirement |
| [Claude Code Usage Monitor](https://github.com/raviboth/ccusage) | Tray UI, local history, undocumented usage endpoint using stored OAuth credentials | No credential extraction; official status-line payload or manual snapshots |
| [Multi-agent observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) | Hook events and real-time multi-agent monitoring | Standard telemetry with Phoenix and provisioned Grafana |
| [claudestat](https://github.com/DeibyGS/claudestat) | Hook-based local execution/cost monitoring | Provider-neutral domain with explicit quota evidence |
| [Phoenix](https://github.com/Arize-ai/phoenix) | OTLP/OpenInference trace investigation | Integrated deep investigation; do not rebuild it |

TraceQuota combines local operation, standard telemetry, explicit interaction/task correlation, main/subagent accounting, quota before/after evidence, Phoenix traces and Grafana time series. This is intended positioning, not a claim that competitors lack every feature. Names suggested in the brief are not assumed to identify maintained repositories. No third-party project code was copied.
