# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

from dataclasses import dataclass
from decimal import Decimal

from .domain import utc


@dataclass
class Filters:
    client: str | None = None
    surface: str | None = None
    runtime: str | None = None
    integration_type: str | None = None
    provider: str | None = None
    billing_platform: str | None = None
    model: str | None = None
    project: str | None = None
    repository: str | None = None
    agent: str | None = None
    pricing_confidence: str | None = None
    since: str | None = None
    until: str | None = None

    def __post_init__(self):
        from fastapi import HTTPException

        for name in ("since", "until"):
            if getattr(self, name):
                try:
                    setattr(self, name, utc(getattr(self, name)))
                except (ValueError, TypeError) as exc:
                    raise HTTPException(422, "Invalid date filter") from exc
        if self.since and self.until and self.until < self.since:
            raise HTTPException(422, "Through date precedes from date")

    def matches(self, event, task):
        dimensions = {
            **task.data,
            **event,
            "client": event.get("client_id", task.client_id),
            "model": event.get("model_resolved", event.get("model")),
            "project": task.project,
            "repository": task.data.get("repository"),
            "pricing_confidence": (event.get("pricing") or {}).get(
                "confidence", "legacy" if event.get("pricing") else "unknown"
            ),
        }
        for key, wanted in vars(self).items():
            if not wanted:
                continue
            if key == "since":
                if event["timestamp"] < utc(wanted):
                    return False
            elif key == "until":
                if event["timestamp"] > utc(wanted):
                    return False
            elif dimensions.get(key, "unknown") != wanted:
                return False
        return True


def cost_summary(events):
    complete, partial, observed = [], [], []
    components = {}
    confidences = {}
    unknown_models = {}
    for event in events:
        pricing = event.get("pricing") or {}
        value = pricing.get("total", pricing.get("usd"))
        part = pricing.get("partial_total", value)
        if value is not None:
            complete.append(Decimal(str(value)))
        if part is not None:
            partial.append(Decimal(str(part)))
        reported = event.get("observed_provider_cost", event.get("provider_emitted_cost"))
        if reported is not None:
            observed.append(Decimal(str(reported)))
        confidence = pricing.get("confidence", "legacy" if value is not None else "unknown")
        confidences[confidence] = confidences.get(confidence, 0) + 1
        if value is None:
            model = event.get("model", "unknown")
            unknown_models[model] = unknown_models.get(model, 0) + 1
        for component in pricing.get("components", []):
            key = component["metric"]
            components[key] = components.get(key, Decimal(0)) + Decimal(component["subtotal"])
    full = sum(complete, Decimal(0)) if events and len(complete) == len(events) else None
    return {
        "estimated_api_equivalent_cost": str(full) if full is not None else None,
        "estimated_api_cost": str(full) if full is not None else None,
        "priced_partial_cost": str(sum(partial, Decimal(0))) if partial else None,
        "observed_provider_cost": str(sum(observed, Decimal(0))) if observed else None,
        "unpriced_requests": len(events) - len(complete),
        "pricing_confidence": confidences,
        "unknown_models": unknown_models,
        "cost_components": {k: str(v) for k, v in components.items()},
        "subscription_cost": None,
        "cost_kind": "API-equivalent workload estimate; subscription bill is unknown",
    }


def usage_summary(events):
    keys = ("input_total", "input_uncached", "output_total", "cache_read", "cache_write", "reasoning")
    result = {}
    for key in keys:
        measured = [e.get("usage", {}).get(key) for e in events]
        known = [v for v in measured if v is not None]
        result[key] = {
            "total": sum(known) if known else None,
            "known_calls": len(known),
            "unknown_calls": len(measured) - len(known),
        }
    return result


def quota_evidence(snapshots, task, providers):
    from datetime import datetime, timedelta
    from .domain import quota_delta

    start, end = task.started_at, task.data.get("completed_at")
    cutoff = utc(datetime.fromisoformat(start) - timedelta(hours=24))
    after_cutoff = utc(datetime.fromisoformat(end) + timedelta(minutes=15)) if end else None
    result = []
    for provider in sorted(providers):
        account = task.data.get("provider_accounts", {}).get(provider, task.data.get("account", "default"))
        matching = sorted(
            [
                q
                for q in snapshots
                if q["provider"] == provider
                and q["account"] == account
                and q["demo"] == task.data.get("demo", False)
                and (not q.get("session_id") or q["session_id"] == task.session_id)
                and (not q.get("task_id") or q["task_id"] == task.id)
            ],
            key=lambda q: q["captured_at"],
        )
        before = next((q for q in reversed(matching) if cutoff <= q["captured_at"] <= start), None)
        after = next((q for q in matching if end and end <= q["captured_at"] <= after_cutoff), None)
        result.append(
            {
                "provider": provider,
                "account": account,
                "before": before,
                "after": after,
                "delta": quota_delta(before, after),
            }
        )
    return result
