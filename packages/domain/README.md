# Domain interface

Executable implementation: `apps/api/tracequota/domain.py` and `db.py`. Provider → project → session → task → normalized request/tool records, agent identifiers and parent identifiers, independent token categories, versioned cost metadata and sourced quota evidence. `QuotaProvider.snapshot` is the extension point. Manual, capacity-estimated and documented status-line providers are available; undocumented collection remains disabled. See ARCHITECTURE.md for V1 packaging decisions.
