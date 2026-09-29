# Cursor → TraceQuota

Status: metadata adapter implemented and fixture-tested; native Cursor execution remains untested. Cursor hooks do **not** provide measured model token usage, API cost or subscription quota. TraceQuota does not infer those from model names, prompts or tool activity. Checked against [official Cursor hooks](https://cursor.com/docs/hooks) on 2026-09-29.

## Install the local hook

Keep the Docker stack running. Host Python 3 is required for this optional adapter. From the repository checkout, on macOS/Linux:

```bash
mkdir -p ~/.cursor/hooks
cp integrations/cursor/hook.py ~/.cursor/hooks/tracequota.py
```

Merge [hooks.example.json](../../integrations/cursor/hooks.example.json) into `~/.cursor/hooks.json`; preserve unrelated hooks. If that file does not exist, copy the example there. Commands in user-level hooks run relative to the user Cursor directory. On Windows copy the script into the equivalent user `.cursor/hooks` directory and replace `python3` with `python` in the example. Use a Cursor version supporting the documented hooks and open a new Agent session after configuration.

The adapter handles `sessionStart`, `sessionEnd`, `beforeSubmitPrompt`, `stop`, `postToolUse` and `postToolUseFailure`. It sends session/generation/event IDs, client version, requested model name, a generic tool category, status and duration to `http://127.0.0.1:8080/api/hooks/cursor`. No provider is inferred from the client or model label. A session bucket and interaction buckets are distinct; retries with the same event/tool identity are deduplicated. These events are not a complete feature-task or subagent accounting system.

Prompt text, transcripts, tool inputs/outputs, email, working-directory paths and workspace roots are discarded on the host before forwarding. Unknown/custom tool names become `Tool`; MCP server names become `MCP`. Projects default to `unassigned`; optionally set `TRACEQUOTA_PROJECT` to an intentionally safe label in Cursor's environment. `TRACEQUOTA_URL` can change the web port, but accepts loopback HTTP(S) endpoints only and rejects redirects. Failures have a one-second network timeout, produce no input logs and never block prompt submission. No credentials, third-party Python libraries or model API calls are needed.

## Verify and remove

Use Cursor normally, then select **Live data** and inspect Integrations/Tasks. Session and tool metadata can appear while token usage and pricing remain unavailable. Synthetic tests cannot prove that an installed Cursor version has executed the hook. The requested model label is descriptive metadata, not evidence of a billed call or resolved provider.

To disable, remove only these TraceQuota commands from `~/.cursor/hooks.json`. Remove the copied script after removing its entries. Existing ledger data remains until deliberately removed through the documented data lifecycle. The default pipeline never reads Cursor's internal databases or account credentials.
