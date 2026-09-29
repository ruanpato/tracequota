# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Cursor hook metadata, independent of provider accounting and private content."""

from time import time_ns
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from .telemetry import digest, normalise


class CursorHook(BaseModel):
    hook_event_name: Literal[
        "sessionStart", "sessionEnd", "beforeSubmitPrompt", "stop", "postToolUse", "postToolUseFailure"
    ]
    session_id: str = Field(min_length=1, max_length=160)
    generation_id: str = Field(default="session", max_length=160)
    event_id: str = Field(default_factory=lambda: str(uuid4()), max_length=160)
    cursor_version: str = Field(default="unknown", max_length=80)
    model: str = Field(default="unknown", max_length=160)
    tool_name: str = Field(default="Tool", max_length=80)
    tool_use_id: str | None = Field(default=None, max_length=160)
    duration_ms: float | None = Field(default=None, ge=0, le=86400000)
    status: Literal["completed", "aborted", "error", "window_close", "user_close"] = "completed"
    project: str = Field(default="unassigned", max_length=256)


def record(payload: CursorHook):
    event = payload.hook_event_name
    session_event = event in ("sessionStart", "sessionEnd")
    task_id = digest("local", "cursor", payload.session_id, "session" if session_event else payload.generation_id)
    attrs = {
        "service.name": "cursor",
        "tracequota.client.id": "cursor",
        "tracequota.client.version": payload.cursor_version,
        "tracequota.client.surface": "ide",
        "tracequota.runtime.name": "cursor",
        "tracequota.integration.type": "tracequota_adapter",
        "session.id": payload.session_id,
        "tracequota.task.id": task_id,
        "tracequota.task.kind": "session_activity" if session_event else "interaction",
        "tracequota.task.title": "Cursor session activity" if session_event else "Cursor interaction",
        "project.name": payload.project,
        "event.name": "cursor." + event,
        "gen_ai.request.model": payload.model,
    }
    if event in ("postToolUse", "postToolUseFailure"):
        attrs["openinference.span.kind"] = "TOOL"
        # Custom tool names may contain sensitive server identifiers.
        attrs["tool_name"] = (
            payload.tool_name
            if payload.tool_name in ("Shell", "Read", "Write", "Grep", "Delete", "Task")
            else "MCP"
            if payload.tool_name == "MCP" or payload.tool_name.startswith("MCP:")
            else "Tool"
        )
        if attrs["tool_name"] == "MCP":
            attrs["gen_ai.tool.type"] = "mcp"
    if payload.duration_ms is not None:
        attrs["duration_ms"] = payload.duration_ms
    raw = {
        "timeUnixNano": str(time_ns()),
        "attributes": [{"key": k, "value": {"stringValue": str(v)}} for k, v in attrs.items()],
    }
    rec = normalise({"resourceLogs": [{"scopeLogs": [{"logRecords": [raw]}]}]}, "logs")[0]
    identity = payload.tool_use_id or payload.event_id
    rec["id"] = digest("cursor-hook", payload.session_id, payload.generation_id, event, identity)
    rec["status"] = "failed" if event == "postToolUseFailure" else "completed"
    return rec, task_id
