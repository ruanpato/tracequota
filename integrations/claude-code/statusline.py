# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Optional host adapter. Python stdlib only; never reads provider credentials."""

import json
import os
import sys
from urllib.request import Request, urlopen


def forward(payload, endpoint="http://localhost:8080"):
    limits = payload.get("rate_limits", {})
    if not limits:
        return False
    safe = {"session_id": payload.get("session_id"), "rate_limits": {}}
    for key in ("five_hour", "seven_day"):
        if isinstance(limits.get(key), dict):
            safe["rate_limits"][key] = {k: limits[key][k] for k in ("used_percentage", "resets_at") if k in limits[key]}
    if not safe["rate_limits"]:
        return False
    request = Request(
        endpoint.rstrip("/") + "/api/quota/statusline",
        data=json.dumps(safe).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=2) as response:
        return response.status == 200


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        forward(data, os.getenv("TRACEQUOTA_URL", "http://localhost:8080"))
        print("TraceQuota · local quota snapshot")
    except Exception:
        # Observability must not interrupt the agent; no input or exceptions are printed.
        print("TraceQuota · quota unavailable")
