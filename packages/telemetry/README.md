# Telemetry interface

Executable implementation: `apps/api/tracequota/telemetry.py`. `normalise(payload, signal)` maps OTLP resources/scopes/records into safe domain records. `attributes` is the persistence allowlist. Collector and API must retain matching allowlists. Extend adapters without coupling quota accounting to a provider. Add fixtures for changes in semantic conventions and preserve original request identity for deduplication.
