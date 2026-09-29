# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Docker Desktop/Engine acceptance, identical on PowerShell, macOS and Linux.
Requires only Docker when invoked through the documented commands individually;
this optional host orchestrator uses Python 3.
"""

import subprocess


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True)


compose("config", "--quiet")
compose("up", "-d", "--build", "--wait", "--wait-timeout", "240")
compose("run", "--rm", "tracequota-doctor")
compose("run", "--rm", "tracequota-smoke")
compose("down")
compose("up", "-d", "--wait", "--wait-timeout", "240")
compose("run", "--rm", "tracequota-doctor")
compose("run", "--rm", "tracequota-doctor", "python", "tools/persistence.py")
print("PASS: full pipeline and persisted task/quota data across down/up.")
