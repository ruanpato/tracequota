# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

from datetime import datetime, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator

CATEGORIES = ("input", "output", "cache_read", "cache_write")
PRICING_DATE = "2026-09-28"


def utc(value=None):
    if value is None:
        dt = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def estimate(model, tokens, at, attrs=None):
    # Legacy example/helper API; authoritative ledger pricing uses the synced DB registry.
    from .pricing import calculate, load_registry

    catalogs, version = load_registry()
    attrs = attrs or {}
    usage = dict(zip(("input_uncached", "output_total", "cache_read", "cache_write"), (tokens[k] for k in CATEGORIES)))
    usage["input_total"] = tokens["input"] + tokens["cache_read"] + tokens["cache_write"]
    result = calculate(
        catalogs,
        version,
        "anthropic",
        model,
        usage,
        at,
        {
            "billing_platform": "anthropic",
            "service_tier": attrs.get("speed", attrs.get("tracequota.pricing.variant", "standard")),
            "region": "global",
            "cache_write_ttl": attrs.get("tracequota.cache_write_ttl", "5m"),
        },
    )
    if result["total"] is None:
        return None
    return {
        **result,
        "usd": result["total"],
        "version": PRICING_DATE,
        "cache_write_ttl": attrs.get("tracequota.cache_write_ttl", "5m"),
    }


class Window(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: Literal["rolling", "weekly", "fixed"] = "rolling"
    used_percent: float = Field(ge=0, le=100)
    reset_at: str | None = None

    @field_validator("reset_at")
    @classmethod
    def validate_reset(cls, value):
        return utc(value) if value else None


class Snapshot(BaseModel):
    id: str | None = Field(default=None, max_length=160)
    provider: str = Field(default="anthropic", min_length=1, max_length=80)
    account: str = Field(default="default", min_length=1, max_length=160)
    session_id: str | None = Field(default=None, max_length=160)
    task_id: str | None = Field(default=None, max_length=160)
    captured_at: str = Field(default_factory=utc)
    source: Literal["official", "manual", "estimated", "experimental"] = "manual"
    demo: bool = False
    windows: list[Window] = Field(min_length=1, max_length=20)

    @field_validator("captured_at")
    @classmethod
    def validate_time(cls, value):
        return utc(value)

    @field_validator("windows")
    @classmethod
    def unique_windows(cls, value):
        if len({v.name for v in value}) != len(value):
            raise ValueError("window names must be unique")
        return value


def quota_delta(before, after):
    if not before or not after:
        return []
    result = []
    for b in before["windows"]:
        a = next((w for w in after["windows"] if w["name"] == b["name"]), None)
        if not a:
            continue
        reset = (
            b.get("reset_at") != a.get("reset_at")
            or bool(b.get("reset_at") and before["captured_at"] < b["reset_at"] <= after["captured_at"])
            or a["used_percent"] < b["used_percent"]
        )
        result.append(
            {
                "name": b["name"],
                "before": b["used_percent"],
                "after": a["used_percent"],
                "delta_pp": None if reset else round(a["used_percent"] - b["used_percent"], 4),
                "reset_crossed": reset,
                "source_before": before["source"],
                "source_after": after["source"],
                "attribution": "account window change; concurrent tasks may contribute",
            }
        )
    return result


class QuotaProvider(Protocol):
    def snapshot(self, **kwargs) -> Snapshot: ...


class ManualQuotaProvider:
    def snapshot(self, **kwargs):
        return Snapshot(**{**kwargs, "source": "manual"})


class EstimatedQuotaProvider:
    def snapshot(self, *, used_units: float, capacity: float, window="5h", **kwargs):
        if capacity <= 0 or used_units < 0:
            raise ValueError("positive explicit capacity and nonnegative units required")
        return Snapshot(
            source="estimated",
            windows=[Window(name=window, used_percent=min(100, used_units / capacity * 100))],
            **kwargs,
        )


class OfficialQuotaProvider:
    def snapshot(self, **kwargs):
        # The caller supplies only the documented status-line payload.
        payload = kwargs.pop("payload")
        windows = []
        for key, name, kind in [("five_hour", "5h", "rolling"), ("seven_day", "weekly", "weekly")]:
            w = payload.get("rate_limits", {}).get(key)
            if w and w.get("used_percentage") is not None:
                reset = datetime.fromtimestamp(w["resets_at"], timezone.utc) if w.get("resets_at") else None
                windows.append(
                    Window(
                        name=name, type=kind, used_percent=w["used_percentage"], reset_at=utc(reset) if reset else None
                    )
                )
        return Snapshot(source="official", session_id=payload.get("session_id"), windows=windows, **kwargs)


class ExperimentalClaudeProvider:
    def snapshot(self, **kwargs):
        raise NotImplementedError(
            "No undocumented endpoint, credential scraping or quota-consuming probe is implemented"
        )
