# Contributing a pricing rule

1. Read the provider's current official pricing documentation. Record its URL, title and verification date; avoid secondary pricing aggregators.
2. Edit `pricing/providers/<provider>.json`. Add an exact canonical model ID and only verified aliases. Ordinary new models/rates require JSON edits, not engine changes.
3. Add a uniquely named rule with an effective start, exclusive optional end, billing platform, tier, region, context bounds and optional TTL. Price strings must be finite and nonnegative. Explain unknown historical start dates and excluded charges in notes.
4. Use a supported metric/unit pair. Missing required quantities produce partial estimates. Reasoning already included in output must not receive a separate rate. Add optional non-token rates only when telemetry can measure that unit; free account allowances cannot be guessed per call.
5. Close an older effective interval before adding changed rates. Do not overlap conditions/time/context or silently reinterpret an alias. Do not invent earlier prices. A gap is allowed and yields unknown cost.
6. Add manually calculated examples and boundary tests to `tests/test_pricing.py`. Test cache semantics and missing measurements.
7. Run `PYTHONPATH=apps/api .venv/bin/python -m tracequota pricing validate`, `.venv/bin/python -m pytest -q`, and formatting checks. On Windows use the equivalent environment setting and `.venv\Scripts\python.exe`, or run the existing Compose test service.
8. Update `pricing/CHANGELOG.md` and the semantic catalog version, then submit a GitHub PR. A later release ships the new files; local sync atomically imports the content hash. Historical call estimates keep their original rule/hash/components.

Validation rejects unknown properties, duplicate rule IDs/model aliases, missing providers/models/source metadata, invalid periods, negative/nonfinite rates, unknown units and ambiguous overlaps. Formatting/order of JSON keys does not change the canonical hash. Source/rate/condition changes do. The checked-in JSON Schema must match `Catalog.model_json_schema()` if the schema is deliberately extended.
