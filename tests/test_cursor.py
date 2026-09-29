# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.error import HTTPError

import pytest

from integrations.cursor.hook import forward, metadata


def test_hook_discards_private_input(monkeypatch):
    monkeypatch.delenv("TRACEQUOTA_PROJECT", raising=False)
    raw = {
        "hook_event_name": "postToolUse",
        "conversation_id": "fixture-session",
        "generation_id": "fixture-turn",
        "tool_name": "MCP:private-server",
        "duration": 12,
        "model_id": "fixture-model",
        "prompt": "PRIVATE",
        "tool_input": "PRIVATE",
        "tool_output": "PRIVATE",
        "cwd": "/private/project",
        "user_email": "private@example.invalid",
        "transcript_path": "/private/transcript",
    }
    data = metadata(raw)
    assert data["tool_name"] == "MCP" and data["duration_ms"] == 12
    assert "PRIVATE" not in json.dumps(data) and "/private/" not in json.dumps(data)
    assert data["project"] == "unassigned"


def test_cursor_metadata_replay_and_separate_generations(client):
    base = {
        "session_id": "fixture-cursor",
        "generation_id": "fixture-turn",
        "event_id": "fixture-event",
        "model": "fixture-model",
        "prompt": "PRIVATE",
        "tool_input": "PRIVATE",
    }
    for event in ("sessionStart", "beforeSubmitPrompt", "postToolUse", "stop", "sessionEnd"):
        payload = {
            **base,
            "hook_event_name": event,
            "tool_name": "Read",
            "tool_use_id": "fixture-tool",
            "duration_ms": 12,
        }
        for _ in range(2):
            response = client.post("/api/hooks/cursor", json=payload)
            assert response.status_code == 200
            assert response.json() == ({"continue": True} if event == "beforeSubmitPrompt" else {})
    rows = client.get("/api/tasks?client=cursor").json()
    assert len(rows) == 2 and {r["kind"] for r in rows} == {"interaction", "session_activity"}
    turn = next(r for r in rows if r["kind"] == "interaction")
    detail = client.get("/api/tasks/" + turn["id"]).json()
    assert detail["llm_calls"] == 0 and detail["tool_calls"] == 1
    assert len(detail["events"]) == 3
    assert detail["status"] == "completed" and detail["client_id"] == "cursor"
    assert not detail["models"]
    assert all(q["before"] is None and q["after"] is None for q in detail["quota_by_provider"])
    assert detail["estimated_api_cost"] is None
    assert all(usage["total"] is None for usage in detail["usage"].values())
    assert "PRIVATE" not in json.dumps(detail)
    assert (
        client.post(
            "/api/hooks/cursor",
            json={
                **base,
                "generation_id": "another-turn",
                "event_id": "fixture-event",
                "hook_event_name": "beforeSubmitPrompt",
            },
        ).status_code
        == 200
    )
    assert len(client.get("/api/tasks?client=cursor").json()) == 3
    descriptor = next(c for c in client.get("/api/integrations").json()["clients"] if c["id"] == "cursor")
    assert descriptor["capabilities"]["tokens"] == "unsupported"
    assert descriptor["capabilities"]["cost"] == "unsupported"


@pytest.mark.parametrize(
    "endpoint",
    ["https://example.invalid", "http://user:password@localhost", "http://localhost/path", "http://localhost?query=1"],
)
def test_nonlocal_endpoints_rejected(endpoint):
    with pytest.raises(ValueError, match="loopback"):
        forward({}, endpoint)


def test_local_redirect_is_not_followed():
    calls = []

    class Redirect(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(self.path)
            self.send_response(302)
            self.send_header("Location", "/redirected")
            self.end_headers()

        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Redirect)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(HTTPError):
            forward({}, f"http://127.0.0.1:{server.server_port}")
        assert calls == ["/api/hooks/cursor"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_unavailable_collector_never_blocks_cursor(monkeypatch, capsys):
    from io import StringIO
    from integrations.cursor import hook

    monkeypatch.setattr(hook.sys, "stdin", StringIO('{"hook_event_name":"beforeSubmitPrompt", "prompt":"PRIVATE"}'))

    def unavailable(*args):
        raise OSError("Unavailable")

    monkeypatch.setattr(hook, "forward", unavailable)
    hook.main()
    assert json.loads(capsys.readouterr().out) == {"continue": True}


def test_cursor_payload_limits(client):
    assert (
        client.post(
            "/api/hooks/cursor", json={"session_id": "fixture", "hook_event_name": "postToolUse", "duration_ms": -1}
        ).status_code
        == 422
    )
