# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Synthetic contract verification; does not certify native client integrations."""

from decimal import Decimal

from smoke_helpers import eventually


def check_multi(client, api, day):
    def check():
        mixed = client.get(api + f"/api/tasks/multi-demo-{day}-03").json()
        assert mixed["client_id"] == "openclaw" and set(mixed["providers"]) == {"openai", "anthropic"}
        calls = [e for e in mixed["events"] if e["kind"] == "llm"]
        assert all(e["pricing"]["total"] is not None for e in calls)
        assert Decimal(mixed["estimated_api_equivalent_cost"]) == sum(
            (Decimal(e["pricing"]["total"]) for e in calls), Decimal(0)
        )
        assert {q["provider"] for q in mixed["quota_by_provider"]} == {"openai", "anthropic"}
        for query, expected in [
            ("client=codex", "codex"),
            ("client=openclaw&provider=openai", "openclaw"),
            ("client=gemini_cli&provider=google", "gemini_cli"),
        ]:
            tasks = client.get(api + "/api/tasks?demo=true&" + query).json()
            assert tasks and all(t["client_id"] == expected for t in tasks)
        scoped = client.get(
            api + f"/api/overview?demo=true&client=openclaw&provider=openai&since={day}T00:00:00Z&until={day}T23:59:59Z"
        ).json()
        assert set(scoped["costs"]["client_id"]) == {"openclaw"} and set(scoped["costs"]["provider"]) == {"openai"}
        assert Decimal(scoped["estimated_api_equivalent_cost"]) == sum(
            Decimal(e["pricing"]["total"]) for e in calls if e["provider"] == "openai"
        )
        assert client.get(api + "/api/tasks?model=gpt-6-sol&demo=true").json()
        return {
            "multi_provider_task": mixed["id"],
            "mixed_task_cost": mixed["estimated_api_equivalent_cost"],
            "providers": mixed["providers"],
            "client_provider_filters": True,
            "model_filter": True,
            "quota_providers": 2,
        }

    result = eventually(check)
    before = client.get(api + "/api/pricing/status").json()
    first = client.post(api + "/api/pricing/sync").json()
    second = client.post(api + "/api/pricing/sync").json()
    assert first["catalog_version"] == second["catalog_version"] == before["database_hash"] and not second["imported"]
    print("PASS: synthetic clients, mixed-provider task cost/quota, filters and idempotent pricing sync.")
    return {**result, "catalog_hash": second["catalog_version"], "sync_idempotent": True}
