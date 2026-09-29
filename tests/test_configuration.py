# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_compose_is_local_and_has_persistent_services():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    required = {"postgres", "tracequota-api", "tracequota-web", "otel-collector", "phoenix", "prometheus", "grafana"}
    assert required <= compose["services"].keys()
    for service in compose["services"].values():
        assert not service.get("privileged") and service.get("network_mode") != "host"
        assert all(port.startswith("127.0.0.1:") for port in service.get("ports", []))
        assert "docker.sock" not in str(service)
    assert len(compose["volumes"]) == 4
    phoenix = compose["services"]["phoenix"]["environment"]
    assert phoenix["PHOENIX_DISABLE_AGENT_ASSISTANT"] == "true"
    assert phoenix["PHOENIX_ENABLE_MCP_SERVER"] == "false"


def test_privacy_allowlist_in_all_collector_pipelines():
    collector = yaml.safe_load((ROOT / "infrastructure/otel/collector.yml").read_text())
    for pipeline in collector["service"]["pipelines"].values():
        assert "transform/privacy" in pipeline["processors"]
    assert 'set(body, "")' in str(collector)
    assert collector["processors"]["filter/private_events"]["traces"]["spanevent"] == ["true"]
    assert "filter/private_events" in collector["service"]["pipelines"]["traces"]["processors"]
    assert "input.value" not in str(collector) and "tool_input" not in str(collector)


def test_migration_upgrade_and_second_start(tmp_path):
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + str(tmp_path / "migrate.db"),
        "PYTHONPATH": str(ROOT / "apps/api"),
    }
    command = [sys.executable, "-m", "alembic", "-c", str(ROOT / "apps/api/alembic.ini"), "upgrade", "head"]
    for _ in range(2):
        assert subprocess.run(command, env=env, capture_output=True).returncode == 0
