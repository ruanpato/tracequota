# Gemini CLI → TraceQuota

Status: native OTel documented upstream; TraceQuota live integration **untested**. Checked 2026-09-28 against [official telemetry documentation](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/telemetry.md) and [local development](https://github.com/google-gemini/gemini-cli/blob/main/docs/local-development.md).

Start the existing local stack and merge telemetry settings into the configuration used by your CLI:

```json
{
  "telemetry": {
    "enabled": true,
    "target": "local",
    "otlpEndpoint": "http://localhost:4318",
    "otlpProtocol": "http",
    "logPrompts": false
  }
}
```

Leave `outfile` unset when exporting to the Collector; upstream file output overrides the endpoint. Restart your CLI. The same JSON works across host operating systems. Shell environment equivalents are documented upstream; set `GEMINI_TELEMETRY_LOG_PROMPTS=false` explicitly if environment overrides are used. Do not configure Google Cloud telemetry for this local destination.

Gemini CLI is the client, Google is the provider, and direct Gemini API/Vertex/subscription access are different billing contexts. Native metadata that cannot establish those distinctions stays partial. The bundled direct Google catalog supports Gemini 2.5 Pro context tiers and measured cache storage token-hours. Thinking-inclusive output is billed once. Missing thinking/output semantics or cache/storage quantities prevents a complete estimate.

Use Integrations to distinguish live export from synthetic fixtures. Inspect canonical `usage` coverage and call pricing warnings before interpreting cost. No official Google subscription quota collector is shipped; use independent provider/account evidence. The multi-client demo covers explicit Gemini CLI/Google data without invoking Gemini.
