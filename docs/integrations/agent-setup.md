# Configure integrations with a coding agent

The Integrations page offers a copyable setup prompt for each implemented integration. Prompts follow the selected interface language and link to the relevant repository guide. Planned adapters have no setup prompt. Review the proposed local settings changes; a prompt cannot grant a capability the client does not support.

For Claude Code and Codex, an optional host Python 3 helper previews a configuration merge without printing existing user settings:

```bash
python3 tools/configure_local_clients.py
python3 tools/configure_local_clients.py --apply
```

Use `python` on Windows. `--client claude` or `--client codex` selects one client; `--otlp-port` and `--web-port` support changed ports. Apply makes private timestamped backups beside each user settings file, then preserves unrelated settings, authentication and permissions. It uses `CODEX_HOME` or the standard user `.codex/config.toml`, and the user's `.claude/settings.json`. Existing custom Codex OTel settings require a manual merge so another telemetry destination is not silently overwritten. An existing Claude status line is preserved; otherwise macOS/Linux receives the repository's optional quota adapter. Keep the checkout available when using that status line. Backups and generated machine-specific paths stay outside the repository. Restore a backup to undo the configuration, then start a new client session.

The helper enables loopback-only logs/traces/metrics export with content capture disabled. It does not install clients, authenticate, launch an agent, consume provider quota or certify native telemetry. Existing sessions may retain their old configuration; start a new CLI or Desktop Local session. Ordinary Chat/Cowork/cloud environments do not automatically use these settings. Use the client guide to check version and environment requirements.

A reusable instruction for your agent:

> Configure my installed coding client to send metadata to local TraceQuota. Read the client guide in this repository. Verify Docker services and http://127.0.0.1:8080/health first. Back up and merge user settings while preserving authentication, permissions and unrelated configuration. Use loopback endpoints, keep content capture disabled, and respect the client's documented capability limits. Validate without making model requests. Explain what new session or normal user activity is needed to observe real telemetry, and distinguish configured settings from verified live data.

If the repository is private, the agent needs existing authorized checkout access. Never embed GitHub/provider tokens in the prompt. See [Claude Code](claude-code.md), [Codex](codex.md) and [Cursor](cursor.md) for configuration and verification details.
