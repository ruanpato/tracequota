# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import os
import subprocess
import sys

subprocess.run([sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"], check=True)
if os.getenv("TRACEQUOTA_PRICING_SYNC", "true").lower() == "true":
    subprocess.run([sys.executable, "-m", "tracequota", "pricing", "sync"], check=True)
subprocess.run(
    [sys.executable, "-m", "uvicorn", "tracequota.main:app", "--host", "0.0.0.0", "--port", "8000"], check=True
)
