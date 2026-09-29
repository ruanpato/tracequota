# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import json
import os

import pytest

from tools.configure_local_clients import claude_config, codex_config, save, tomllib


def test_codex_preserves_existing_configuration_and_is_idempotent():
    original = 'model = "example-model"\n[projects."/example/repo"]\ntrust_level = "trusted"\n'
    result = codex_config(original, 4318)
    data = tomllib.loads(result)
    assert data["model"] == "example-model"
    assert data["projects"] == tomllib.loads(original)["projects"]
    assert data["otel"]["log_user_prompt"] is False
    assert all(
        data["otel"][name]["otlp-http"]["endpoint"].startswith("http://127.0.0.1:4318/")
        for name in ("exporter", "trace_exporter", "metrics_exporter")
    )
    assert codex_config(result, 4318) == result
    with pytest.raises(ValueError, match="custom"):
        codex_config('[otel]\nenvironment="custom"', 4318)


def test_claude_preserves_custom_settings_and_deduplicates_hooks():
    original = json.dumps(
        {
            "permissions": {"allow": ["Read"]},
            "statusLine": {"type": "command", "command": "custom"},
            "env": {"UNRELATED_SETTING": "keep"},
            "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "custom"}]}]},
        }
    )
    result = claude_config(original, 4318, 8080)
    data = json.loads(result)
    assert data["permissions"] == {"allow": ["Read"]}
    assert data["statusLine"]["command"] == "custom"
    assert data["env"]["UNRELATED_SETTING"] == "keep"
    assert data["env"]["OTEL_LOG_USER_PROMPTS"] == "0"
    assert len(data["hooks"]["SessionStart"]) == 2
    assert claude_config(result, 4318, 8080) == result


def test_user_backup_is_private_and_preserves_original(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"original":true}')
    save(path, '{"updated":true}')
    backups = list(tmp_path.glob("*.tracequota-backup-*"))
    assert len(backups) == 1 and backups[0].read_text() == '{"original":true}'
    assert path.read_text() == '{"updated":true}'
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
        assert backups[0].stat().st_mode & 0o777 == 0o600
