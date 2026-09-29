# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Bounded retries for asynchronous telemetry acceptance checks."""

import time

import httpx


def eventually(check, seconds=60):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            return check()
        except (AssertionError, httpx.HTTPError, KeyError, ValueError) as exc:
            last = exc
            time.sleep(2)
    raise AssertionError(f"Condition did not become true: {last}")
