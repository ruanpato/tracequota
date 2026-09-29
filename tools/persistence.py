# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import os
import httpx

api = os.getenv("API_URL", "http://tracequota-api:8000")
data = httpx.get(api + "/api/tasks?demo=true&limit=1000").json()
fixture_tasks = [t for t in data if t["id"].startswith(("demo-", "multi-demo-"))]
assert len(fixture_tasks) >= 25
assert all(t["quota_before"] and t["quota_after"] and t["total_token_activity"] > 0 for t in fixture_tasks)
print("PASS: demo task and quota records remain after restart.")
