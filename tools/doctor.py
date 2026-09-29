# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import os
import sys

import httpx

checks = {
    "TraceQuota API": os.getenv("API_URL", "http://tracequota-api:8000") + "/health",
    "Collector": "http://otel-collector:13133",
    "Phoenix": "http://phoenix:6006/healthz",
    "Prometheus": "http://prometheus:9090/-/healthy",
    "Grafana": "http://grafana:3000/api/health",
}
failed = []
for name, url in checks.items():
    try:
        httpx.get(url, timeout=5).raise_for_status()
        print(f"PASS {name}")
    except Exception as exc:
        failed.append(name)
        print(f"FAIL {name}: {exc}")
sys.exit(bool(failed))
