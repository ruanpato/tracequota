# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Non-blocking, metadata-only Cursor hook. No third-party Python dependencies."""

import json
import os
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def metadata(raw):
    result = {
        "hook_event_name": raw.get("hook_event_name"),
        "session_id": str(raw.get("conversation_id") or raw.get("session_id") or "unknown")[:160],
        "generation_id": str(raw.get("generation_id") or "session")[:160],
        "event_id": str(uuid4()),
        "cursor_version": str(raw.get("cursor_version") or "unknown")[:80],
        "model": str(raw.get("model_id") or raw.get("model") or "unknown")[:160],
        "tool_name": str(raw.get("tool_name") or "Tool")[:80],
        "status": raw.get("status", raw.get("reason", "completed")),
        "project": os.getenv("TRACEQUOTA_PROJECT", "unassigned")[:256],
    }
    name = result["tool_name"]
    result["tool_name"] = (
        name
        if name in ("Shell", "Read", "Write", "Grep", "Delete", "Task")
        else "MCP"
        if name.startswith("MCP:")
        else "Tool"
    )
    if result["status"] not in ("completed", "aborted", "error", "window_close", "user_close"):
        result["status"] = "completed"
    if raw.get("tool_use_id"):
        result["tool_use_id"] = str(raw["tool_use_id"])[:160]
    duration = raw.get("duration", raw.get("duration_ms"))
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 <= duration <= 86400000:
        result["duration_ms"] = duration
    return result


def forward(payload, endpoint=None):
    endpoint = endpoint or os.getenv("TRACEQUOTA_URL", "http://127.0.0.1:8080")
    url = urlsplit(endpoint)
    if (
        url.scheme not in ("http", "https")
        or url.hostname not in ("localhost", "127.0.0.1", "::1")
        or url.username
        or url.password
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ValueError("Cursor telemetry must use a loopback endpoint")
    request = Request(
        endpoint.rstrip("/") + "/api/hooks/cursor",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=1) as response:
        return response.status


def main():
    event = ""
    try:
        raw = json.load(sys.stdin)
        event = raw.get("hook_event_name", "")
        forward(metadata(raw))
    except Exception:
        # Observability must never interrupt the coding client or expose input.
        pass
    print(json.dumps({"continue": True} if event == "beforeSubmitPrompt" else {}))


if __name__ == "__main__":
    main()
