# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Constrained, immutable pricing catalogs. No executable configuration or remote fetches."""

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[3] / "pricing"
METRICS = ("input_uncached", "output_total", "cache_read", "cache_write", "reasoning")
UNITS = {
    "million_tokens": Decimal(1000000),
    "request": Decimal(1),
    "thousand_requests": Decimal(1000),
    "million_token_hours": Decimal(1000000),
    "second": Decimal(1),
}


class Data(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Data):
    url: str = Field(pattern=r"^https://", min_length=12)
    title: str = Field(min_length=1)
    checked_at: date


class Rate(Data):
    metric: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    unit: Literal["million_tokens", "request", "thousand_requests", "million_token_hours", "second"]
    rate: str
    required: bool = True

    @field_validator("rate")
    @classmethod
    def positive_decimal(cls, value):
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("rate must be a decimal string") from exc
        if not number.is_finite() or number < 0:
            raise ValueError("rate must be finite and nonnegative")
        return value


class Conditions(Data):
    service_tier: str = Field(default="standard", min_length=1)
    billing_platform: str = Field(min_length=1)
    region: str = Field(default="global", min_length=1)
    context_min: int = Field(default=0, ge=0)
    context_max: int | None = Field(default=None, ge=0)
    cache_write_ttl: str | None = None

    @model_validator(mode="after")
    def bounds(self):
        if self.context_max is not None and self.context_max < self.context_min:
            raise ValueError("context_max must be >= context_min")
        return self


class Rule(Data):
    id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    effective_from: date | datetime
    effective_until: date | datetime | None = None
    conditions: Conditions
    rates: list[Rate] = Field(min_length=1)
    reasoning_billing: Literal["included_in_output", "separate", "unsupported"] = "included_in_output"
    source: Source
    notes: list[str] = Field(default_factory=list)

    @field_validator("effective_from", "effective_until")
    @classmethod
    def timezone_required(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("effective timestamps need a timezone")
        return value

    @model_validator(mode="after")
    def valid(self):
        if self.effective_until and instant(self.effective_until) <= instant(self.effective_from):
            raise ValueError("effective_until must be after effective_from (exclusive)")
        if len({r.metric for r in self.rates}) != len(self.rates):
            raise ValueError("duplicate rate metric")
        if self.reasoning_billing == "included_in_output" and any(r.metric == "reasoning" for r in self.rates):
            raise ValueError("included reasoning must not have a separate rate")
        if self.reasoning_billing == "separate" and not any(r.metric == "reasoning" for r in self.rates):
            raise ValueError("separate reasoning needs a reasoning rate")
        return self


class Model(Data):
    id: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)


class Catalog(Data):
    schema_version: Literal[1] = 1
    version: str = Field(min_length=1)
    currency: Literal["USD"] = "USD"
    provider: str = Field(min_length=1)
    models: list[Model] = Field(min_length=1)
    rules: list[Rule] = Field(min_length=1)

    @model_validator(mode="after")
    def coherent(self):
        names = [n for m in self.models for n in [m.id, *m.aliases]]
        if any(not n for n in names) or len(names) != len(set(names)):
            raise ValueError("duplicate or empty model IDs/aliases")
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("duplicate rule IDs")
        for i, rule in enumerate(self.rules):
            if rule.model_id not in {m.id for m in self.models}:
                raise ValueError(f"unknown model id: {rule.model_id}")
            for other in self.rules[:i]:
                a, b = rule.conditions, other.conditions
                same = rule.model_id == other.model_id and all(
                    getattr(a, k) == getattr(b, k) for k in ("service_tier", "billing_platform", "region")
                )
                ttl_overlap = (
                    a.cache_write_ttl is None or b.cache_write_ttl is None or a.cache_write_ttl == b.cache_write_ttl
                )
                dates = instant(rule.effective_from) < instant(other.effective_until) and instant(
                    other.effective_from
                ) < instant(rule.effective_until)
                context = a.context_min <= (
                    b.context_max if b.context_max is not None else 10**30
                ) and b.context_min <= (a.context_max if a.context_max is not None else 10**30)
                if same and ttl_overlap and dates and context:
                    raise ValueError(f"ambiguous overlapping rules: {rule.id}, {other.id}")
        return self


def instant(value):
    if value is None:
        return datetime.max.replace(tzinfo=timezone.utc)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def load_registry(root=ROOT):
    catalogs = [Catalog.model_validate_json(p.read_text()) for p in sorted((Path(root) / "providers").glob("*.json"))]
    if not catalogs or len({c.provider for c in catalogs}) != len(catalogs):
        raise ValueError("registry needs unique provider catalogs")
    ids = [r.id for c in catalogs for r in c.rules]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate rule IDs across providers")
    payload = [c.model_dump(mode="json") for c in catalogs]
    version = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return catalogs, version


def unknown(version=None, warning="No matching pricing rule"):
    return {
        "currency": "USD",
        "total": None,
        "usd": None,
        "partial_total": None,
        "components": [],
        "pricing_rule_id": None,
        "catalog_version": version,
        "confidence": "unknown",
        "assumptions": [],
        "warnings": [warning],
    }


def calculate(catalogs, version, provider, model, usage, at, dimensions=None):
    dimensions = dict(dimensions or {})
    catalog = next((c for c in catalogs if c.provider == provider), None)
    canonical = next((m.id for m in catalog.models if model == m.id or model in m.aliases), None) if catalog else None
    if canonical is None:
        return unknown(version, f"Unknown provider/model: {provider}/{model}")
    assumptions = []
    for name, default in (("billing_platform", provider), ("service_tier", "standard"), ("region", "global")):
        if dimensions.get(name) in (None, "", "unknown"):
            dimensions[name] = default
            assumptions.append(f"{name} unavailable; {default} pricing assumed")
    when = instant(at)
    candidates = []
    context = (
        dimensions.get("context_tokens") if dimensions.get("context_tokens") is not None else usage.get("input_total")
    )
    for rule in catalog.rules:
        c = rule.conditions
        if rule.model_id != canonical or not (instant(rule.effective_from) <= when < instant(rule.effective_until)):
            continue
        if any(getattr(c, k) != dimensions[k] for k in ("billing_platform", "service_tier", "region")):
            continue
        if c.cache_write_ttl is not None and (dimensions.get("cache_write_ttl") or "5m") != c.cache_write_ttl:
            continue
        if context is None and (c.context_min > 0 or c.context_max is not None):
            continue
        if context is not None and not (
            c.context_min <= context and (c.context_max is None or context <= c.context_max)
        ):
            continue
        candidates.append(rule)
    if len(candidates) != 1:
        return unknown(version, "Pricing conditions unavailable, unsupported, ambiguous, or outside effective period")
    rule = candidates[0]
    warnings = list(usage.get("warnings", []))
    components = []
    for rate in rule.rates:
        quantity = usage.get(rate.metric)
        if rate.metric == "reasoning" and rule.reasoning_billing == "included_in_output":
            continue
        if quantity is None:
            if rate.required:
                warnings.append(f"Missing usage: {rate.metric}")
            continue
        q = Decimal(str(quantity))
        if rate.metric == "output_total" and rule.reasoning_billing == "separate":
            if usage.get("reasoning") is None:
                warnings.append("Reasoning quantity unavailable for separate billing")
                continue
            q -= Decimal(str(usage["reasoning"]))
        if not q.is_finite() or q < 0:
            warnings.append(f"Invalid usage: {rate.metric}")
            continue
        if (
            rate.metric == "cache_write"
            and q > 0
            and rule.conditions.cache_write_ttl
            and not dimensions.get("cache_write_ttl")
        ):
            warnings.append("Cache write TTL unavailable")
            continue
        subtotal = q * Decimal(rate.rate) / UNITS[rate.unit]
        components.append(
            {
                "metric": rate.metric,
                "quantity": str(q),
                "unit": rate.unit,
                "rate": rate.rate,
                "subtotal": format(subtotal, "f"),
            }
        )
    if usage.get("reasoning") and rule.reasoning_billing == "unsupported":
        warnings.append("Reasoning billing unsupported")
    for metric, quantity in usage.items():
        if (
            isinstance(quantity, (int, Decimal))
            and quantity > 0
            and metric not in ("input_total", "reasoning")
            and not any(r.metric == metric for r in rule.rates)
        ):
            warnings.append(f"Unpriced usage: {metric}")
    if usage.get("reasoning") and usage.get("output_semantics") == "unknown":
        warnings.append("Output reasoning semantics unavailable")
    total = sum((Decimal(c["subtotal"]) for c in components), Decimal(0))
    partial = bool(warnings)
    confidence = (
        "partial"
        if partial and components
        else "unknown"
        if not components
        else "estimated"
        if assumptions
        else "high"
        if model != canonical
        else "exact"
    )
    result = {
        "currency": "USD",
        "total": None if partial else format(total, "f"),
        "usd": None if partial else format(total, "f"),
        "partial_total": format(total, "f") if components else None,
        "components": components,
        "pricing_rule_id": rule.id,
        "catalog_version": version,
        "catalog_semver": catalog.version,
        "confidence": confidence,
        "assumptions": assumptions,
        "warnings": warnings,
        "source": rule.source.model_dump(mode="json"),
        "effective_from": str(rule.effective_from),
        "model": canonical,
        "notes": rule.notes,
        "context_tier": {"min_tokens": rule.conditions.context_min, "max_tokens": rule.conditions.context_max},
    }
    if model != canonical:
        result["assumptions"].append("Exact model alias mapped to canonical model")
    return result


def sync(db, root=ROOT):
    from .db import CatalogVersion, PricingRule

    catalogs, version = load_registry(root)
    existing = db.get(CatalogVersion, version)
    now = datetime.now(timezone.utc).isoformat()
    if not existing:
        db.add(
            CatalogVersion(
                id=version,
                imported_at=now,
                last_synced_at=now,
                active=True,
                data=[c.model_dump(mode="json") for c in catalogs],
            )
        )
        db.flush()
        for catalog in catalogs:
            for rule in catalog.rules:
                db.add(
                    PricingRule(
                        id=version + ":" + rule.id,
                        catalog_version=version,
                        rule_id=rule.id,
                        provider=catalog.provider,
                        model_id=rule.model_id,
                        data=rule.model_dump(mode="json"),
                    )
                )
    else:
        existing.last_synced_at = now
        existing.active = True
    from sqlalchemy import select

    for row in db.scalars(select(CatalogVersion).where(CatalogVersion.id != version)):
        row.active = False
    return {
        "catalog_version": version,
        "imported": existing is None,
        "providers": len(catalogs),
        "rules": sum(len(c.rules) for c in catalogs),
        "synced_at": now,
    }


def active_registry(db):
    from sqlalchemy import select
    from .db import CatalogVersion

    row = db.scalar(select(CatalogVersion).where(CatalogVersion.active.is_(True)))
    return ([Catalog.model_validate(c) for c in row.data], row.id) if row else ([], None)


def status(db):
    from sqlalchemy import select
    from .db import CatalogVersion

    catalogs, bundled = load_registry()
    row = db.scalar(select(CatalogVersion).where(CatalogVersion.active.is_(True)))
    return {
        "bundled_hash": bundled,
        "database_hash": row.id if row else None,
        "in_sync": bool(row and row.id == bundled),
        "last_sync": row.last_synced_at if row else None,
        "providers": len(catalogs),
        "models": sum(len(c.models) for c in catalogs),
        "rules": sum(len(c.rules) for c in catalogs),
        "authority": "bundled Git-managed registry",
    }
