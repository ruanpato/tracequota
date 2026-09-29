# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Configure local Claude Code/Codex telemetry without touching credentials."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
START = "# TraceQuota local telemetry"
END = "# End TraceQuota local telemetry"


def save(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(
            path.name + ".tracequota-backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        )
        backup.write_bytes(path.read_bytes())
        backup.chmod(0o600)
    temporary = path.with_name(path.name + ".tracequota-tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def codex_config(original, otlp_port):
    if START in original and END in original:
        original = original[: original.index(START)] + original[original.index(END) + len(END) :]
    parsed = tomllib.loads(original)
    if "otel" in parsed:
        raise ValueError("Existing custom Codex OTel settings: merge the documented loopback exporter fields manually.")
    block = f"""{START}
[otel]
environment = "local"
log_user_prompt = false
exporter = {{ otlp-http = {{ endpoint = "http://127.0.0.1:{otlp_port}/v1/logs", protocol = "binary" }} }}
trace_exporter = {{ otlp-http = {{ endpoint = "http://127.0.0.1:{otlp_port}/v1/traces", protocol = "binary" }} }}
metrics_exporter = {{ otlp-http = {{ endpoint = "http://127.0.0.1:{otlp_port}/v1/metrics", protocol = "binary" }} }}
{END}
"""
    result = original.rstrip() + "\n\n" + block
    tomllib.loads(result)
    return result


def claude_config(original, otlp_port, web_port):
    data = json.loads(original or "{}")
    env = data.setdefault("env", {})
    env.update(
        {
            "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
            "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
            "OTEL_METRICS_EXPORTER": "otlp",
            "OTEL_LOGS_EXPORTER": "otlp",
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{otlp_port}",
            "OTEL_METRICS_INCLUDE_ACCOUNT_UUID": "false",
            "OTEL_METRICS_INCLUDE_SESSION_ID": "true",
            "OTEL_LOG_USER_PROMPTS": "0",
            "OTEL_LOG_ASSISTANT_RESPONSES": "0",
            "OTEL_LOG_TOOL_DETAILS": "0",
            "OTEL_LOG_TOOL_CONTENT": "0",
            "OTEL_LOG_RAW_API_BODIES": "0",
            "TRACEQUOTA_URL": f"http://127.0.0.1:{web_port}",
        }
    )
    for signal in ("LOGS", "METRICS", "TRACES"):
        env[f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT"] = f"http://127.0.0.1:{otlp_port}/v1/{signal.lower()}"
        env[f"OTEL_EXPORTER_OTLP_{signal}_PROTOCOL"] = "http/protobuf"
        env[f"OTEL_EXPORTER_OTLP_{signal}_HEADERS"] = ""
    env["OTEL_EXPORTER_OTLP_HEADERS"] = ""
    # Keep custom resource labels and status lines; never copy them into the repository.
    if "statusLine" not in data and os.name != "nt":
        data["statusLine"] = {
            "type": "command",
            "command": "python3 " + shlex.quote(str(ROOT / "integrations/claude-code/statusline.py")),
        }
    hooks = data.setdefault("hooks", {})
    for event in ("SessionStart", "SessionEnd"):
        item = {"hooks": [{"type": "http", "url": f"http://127.0.0.1:{web_port}/api/hooks/claude"}]}
        entries = hooks.setdefault(event, [])
        if item not in entries:
            entries.append(item)
    return json.dumps(data, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write user settings after a private local backup")
    parser.add_argument("--client", choices=("all", "claude", "codex"), default="all")
    parser.add_argument("--otlp-port", type=int, default=4318)
    parser.add_argument("--web-port", type=int, default=8080)
    args = parser.parse_args()
    if not all(1 <= p <= 65535 for p in (args.otlp_port, args.web_port)):
        parser.error("Ports must be between 1 and 65535")
    plans = []
    if args.client in ("all", "codex"):
        path = Path(os.getenv("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
        original = path.read_text(encoding="utf-8") if path.exists() else ""
        plans.append(("Codex", path, codex_config(original, args.otlp_port)))
    if args.client in ("all", "claude"):
        path = Path.home() / ".claude/settings.json"
        original = path.read_text(encoding="utf-8") if path.exists() else "{}"
        plans.append(("Claude Code", path, claude_config(original, args.otlp_port, args.web_port)))
    for name, path, text in plans:
        if args.apply:
            save(path, text)
        print(f"{name}: {'configured' if args.apply else 'preview ready'}; loopback only, content capture off.")
    print("Start a new client session to load settings. No login or model requests were performed.")


if __name__ == "__main__":
    main()
