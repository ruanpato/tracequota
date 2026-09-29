# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import copy
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from tracequota import db, pricing
from tracequota.pricing import Catalog, calculate, load_registry
from tracequota.usage import normalize

AT = "2026-09-28T12:00:00Z"
DIMS = {"billing_platform": "anthropic", "service_tier": "standard", "region": "global", "cache_write_ttl": "5m"}


def usage(**overrides):
    return {
        "input_total": 3000000,
        "input_uncached": 1000000,
        "cache_read": 1000000,
        "cache_write": 1000000,
        "output_total": 1000000,
        "reasoning": 100000,
        "output_semantics": "inclusive_reasoning",
        **overrides,
    }


def bundled(provider="anthropic", model="claude-sonnet-4-6", u=None, dims=None, at=AT):
    catalogs, version = load_registry()
    return calculate(catalogs, version, provider, model, u or usage(), at, dims or DIMS)


def fixture_catalog():
    catalogs, _ = load_registry()
    catalog = catalogs[0].model_dump(mode="json")
    catalog["models"] = [{"id": "test-model", "aliases": ["test-alias"]}]
    rule = copy.deepcopy(catalog["rules"][0])
    rule.update(id="test/standard", model_id="test-model")
    rule["conditions"]["cache_write_ttl"] = None
    catalog["rules"] = [rule]
    return catalog


def test_known_anthropic_example_cache_and_precision():
    p = bundled()
    assert Decimal(p["total"]) == Decimal("22.05")
    assert [Decimal(c["subtotal"]) for c in p["components"]] == list(map(Decimal, ["3", "15", ".30", "3.75"]))
    assert p["confidence"] == "exact" and p["catalog_version"] and p["pricing_rule_id"]
    p = bundled(u=usage(input_uncached=1, output_total=1, cache_read=1, cache_write=1, input_total=3))
    assert Decimal(p["total"]) == Decimal(".00002205")


def test_cache_ttl_selection_and_missing_ttl_partial_components():
    assert Decimal(bundled(dims={**DIMS, "cache_write_ttl": "1h"})["total"]) == Decimal("24.3")
    p = bundled(dims={**DIMS, "cache_write_ttl": None})
    assert p["total"] is None and p["confidence"] == "partial"
    assert Decimal(p["partial_total"]) == Decimal("18.3")
    assert "Cache write TTL unavailable" in p["warnings"]


def test_reasoning_included_only_once_and_separate_charge():
    assert bundled(u=usage(reasoning=900000))["total"] == bundled(u=usage(reasoning=0))["total"]
    raw = fixture_catalog()
    raw["rules"][0]["reasoning_billing"] = "separate"
    raw["rules"][0]["rates"].append({"metric": "reasoning", "unit": "million_tokens", "rate": "20"})
    p = calculate([Catalog.model_validate(raw)], "test", "anthropic", "test-model", usage(), AT, DIMS)
    # 900k ordinary output at 15 + 100k reasoning at 20, never 1M output plus reasoning.
    assert Decimal(p["total"]) == Decimal("22.55")
    p = calculate([Catalog.model_validate(raw)], "test", "anthropic", "test-model", usage(reasoning=None), AT, DIMS)
    assert p["total"] is None


@pytest.mark.parametrize("tier,factor", [("standard", "1"), ("batch", ".5"), ("flex", ".5"), ("fast", "2")])
@pytest.mark.parametrize("context,long", [(272000, False), (272001, True)])
def test_openai_context_boundary_and_service_tiers(tier, factor, context, long):
    dims = {"billing_platform": "openai", "service_tier": tier, "region": "global", "context_tokens": context}
    p = bundled(
        "openai",
        "gpt-6-sol",
        usage(input_uncached=100000, input_total=context, cache_read=10000, cache_write=0, output_total=1000),
        dims,
    )
    expected = Decimal(".552") if long else Decimal(".212")
    # Long: .4 input + .004 cached + .015 output = .419.
    if long:
        expected = Decimal(".419")
    assert Decimal(p["total"]) == expected * Decimal(factor)


@pytest.mark.parametrize("context,expected", [(200000, ".13625"), (200001, ".2675")])
def test_google_known_short_long_example(context, expected):
    p = bundled(
        "google",
        "gemini-2.5-pro",
        usage(
            input_uncached=100000,
            input_total=context,
            cache_read=10000,
            cache_write=0,
            output_total=1000,
            cache_storage_token_hours=0,
        ),
        {"billing_platform": "google", "service_tier": "standard", "region": "global"},
    )
    assert Decimal(p["total"]) == Decimal(expected)


def test_non_token_measured_charge():
    raw = fixture_catalog()
    raw["rules"][0]["rates"].append({"metric": "tool_requests", "unit": "thousand_requests", "rate": "10"})
    p = calculate([Catalog.model_validate(raw)], "test", "anthropic", "test-model", usage(tool_requests=25), AT, DIMS)
    assert Decimal(p["total"]) == Decimal("22.30")
    p = bundled(u=usage(tool_requests=1))
    assert p["total"] is None and "Unpriced usage: tool_requests" in p["warnings"]


@pytest.mark.parametrize(
    "provider,model,dims,at",
    [
        ("unknown", "claude-sonnet-4-6", DIMS, AT),
        ("anthropic", "claude-sonnet-4-6-20990101", DIMS, AT),
        ("anthropic", "unknown", DIMS, AT),
        ("anthropic", "claude-sonnet-4-6", {**DIMS, "billing_platform": "aws_bedrock"}, AT),
        ("anthropic", "claude-sonnet-4-6", {**DIMS, "region": "unsupported"}, AT),
        ("anthropic", "claude-sonnet-4-6", DIMS, "2026-09-27"),
    ],
)
def test_unknown_or_unsupported_never_zero(provider, model, dims, at):
    p = bundled(provider, model, dims=dims, at=at)
    assert p["total"] is None and p["confidence"] == "unknown" and p["warnings"]


def test_alias_exact_matching_and_temporal_transition_gap():
    raw = fixture_catalog()
    first = raw["rules"][0]
    first["effective_until"] = "2026-10-01"
    second = copy.deepcopy(first)
    second.update(id="test/updated", effective_from="2026-10-01", effective_until=None)
    second["rates"][0]["rate"] = "6"
    raw["rules"].append(second)
    catalog = Catalog.model_validate(raw)
    args = ([catalog], "test", "anthropic", "test-alias", usage())
    old = calculate(*args, "2026-09-30", DIMS)
    new = calculate(*args, "2026-10-01", DIMS)
    assert old["pricing_rule_id"] == first["id"] and Decimal(new["total"]) - Decimal(old["total"]) == 3
    assert old["confidence"] == "high"
    assert calculate([catalog], "test", "anthropic", "test-alias-20260101", usage(), AT, DIMS)["total"] is None
    second["effective_from"] = "2026-10-02"
    catalog = Catalog.model_validate(raw)
    assert calculate([catalog], "test", "anthropic", "test-model", usage(), "2026-10-01", DIMS)["total"] is None


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(provider=""),
        lambda c: c["models"][0].update(id=""),
        lambda c: c["models"][0].update(aliases=["test-model"]),
        lambda c: c["rules"].append(copy.deepcopy(c["rules"][0])),
        lambda c: c["rules"][0].update(effective_from="yesterday"),
        lambda c: c["rules"][0].update(effective_until="2026-09-28"),
        lambda c: c["rules"][0]["rates"][0].update(rate="-1"),
        lambda c: c["rules"][0]["rates"][0].update(rate="NaN"),
        lambda c: c["rules"][0]["rates"][0].update(unit="undefined"),
        lambda c: c["rules"][0].pop("source"),
        lambda c: c["rules"][0].update(expression="arbitrary code"),
        lambda c: c["rules"][0].update(model_id="missing"),
    ],
)
def test_catalog_validation_rejects_invalid_data(change):
    raw = fixture_catalog()
    change(raw)
    with pytest.raises(ValidationError):
        Catalog.model_validate(raw)


def test_overlapping_context_and_temporal_rules_rejected():
    raw = fixture_catalog()
    second = copy.deepcopy(raw["rules"][0])
    second.update(id="conflict")
    raw["rules"].append(second)
    with pytest.raises(ValidationError, match="overlap"):
        Catalog.model_validate(raw)
    raw["rules"][0]["conditions"].update(context_max=200000)
    second["conditions"].update(context_min=200001)
    Catalog.model_validate(raw)


def test_hash_content_idempotency_json_order_and_invalid_json(tmp_path):
    (tmp_path / "providers").mkdir()
    path = tmp_path / "providers/test.json"
    raw = fixture_catalog()
    path.write_text(json.dumps(raw))
    first = load_registry(tmp_path)[1]
    path.write_text(json.dumps(raw, sort_keys=True, indent=4))
    assert first == load_registry(tmp_path)[1]
    raw["rules"][0]["rates"][0]["rate"] = "9"
    path.write_text(json.dumps(raw))
    assert first != load_registry(tmp_path)[1]
    path.write_text("{broken")
    with pytest.raises(ValueError):
        load_registry(tmp_path)


def test_missing_cache_telemetry_partial_not_zero_and_unknown_semantics():
    u = normalize({"gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 10}, "unknown")
    assert u["input_total"] == 100 and u["input_uncached"] is None and u["cache_read"] is None
    p = bundled(u=u)
    assert p["total"] is None and Decimal(p["partial_total"]) == Decimal(".00015")
    assert p["confidence"] == "partial"
    u = normalize(
        {
            "tracequota.usage.input_semantics": "inclusive",
            "gen_ai.usage.input_tokens": 100,
            "cache_read_tokens": 30,
            "cache_creation_tokens": 20,
            "output_tokens": 10,
        },
        "generic_otlp",
    )
    assert u["input_uncached"] == 50 and u["input_total"] == 100 and u["usage_semantics"] == "derived"
    u = normalize(
        {"input_tokens": 100, "cache_read_tokens": 30, "cache_creation_tokens": 20, "output_tokens": 10}, "claude_code"
    )
    assert u["input_uncached"] == 100 and u["input_total"] == 150


def test_zero_is_a_known_price_and_assumptions_are_visible():
    p = bundled(u=usage(input_total=0, input_uncached=0, output_total=0, cache_read=0, cache_write=0, reasoning=0))
    assert Decimal(p["total"]) == 0 and p["confidence"] == "exact"
    p = bundled(dims={"cache_write_ttl": "5m"})
    assert p["confidence"] == "estimated" and len(p["assumptions"]) == 3


def test_sync_database_idempotent_and_active_catalog_persists(client):
    first = client.post("/api/pricing/sync").json()
    second = client.post("/api/pricing/sync").json()
    assert first["catalog_version"] == second["catalog_version"] and second["imported"] is False
    with db.Session() as session:
        assert len(session.scalars(select(db.CatalogVersion)).all()) == 1
        assert len(session.scalars(select(db.PricingRule)).all()) == second["rules"]
    assert client.get("/api/pricing/status").json()["in_sync"] is True


def test_checked_in_schema_matches_validator():
    expected = json.loads((pricing.ROOT / "schema/pricing.schema.json").read_text())
    assert expected == Catalog.model_json_schema()


def test_intraday_effective_timestamp_transition():
    raw = fixture_catalog()
    first = raw["rules"][0]
    first["effective_until"] = "2026-09-28T12:00:00Z"
    second = copy.deepcopy(first)
    second.update(id="noon", effective_from="2026-09-28T12:00:00Z", effective_until=None)
    second["rates"][0]["rate"] = "6"
    raw["rules"].append(second)
    catalog = Catalog.model_validate(raw)
    before = calculate([catalog], "test", "anthropic", "test-model", usage(), "2026-09-28T11:59:59Z", DIMS)
    after = calculate([catalog], "test", "anthropic", "test-model", usage(), "2026-09-28T12:00:00Z", DIMS)
    assert before["pricing_rule_id"] == "test/standard" and after["pricing_rule_id"] == "noon"


def test_missing_required_separate_reasoning_rate_rejected():
    raw = fixture_catalog()
    raw["rules"][0]["reasoning_billing"] = "separate"
    with pytest.raises(ValidationError, match="reasoning rate"):
        Catalog.model_validate(raw)
