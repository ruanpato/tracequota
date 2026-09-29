# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import gzip
import json
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from google.protobuf.json_format import MessageToDict, ParseDict
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from .db import AgentRun, ExecutionSession, Event, MetricObservation, Quota, Session, Task, transaction
from .analytics import Filters, cost_summary, usage_summary, quota_evidence
from . import clients, pricing
from .domain import CATEGORIES, OfficialQuotaProvider, Snapshot, quota_delta, utc
from .telemetry import digest, normalise, sanitise_traces


@asynccontextmanager
async def lifespan(app):
    if os.getenv("TRACEQUOTA_PRICING_SYNC", "true").lower() == "true":
        with transaction() as db:
            pricing.sync(db)
    yield


app = FastAPI(title="TraceQuota", version="0.2.0", lifespan=lifespan)


@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and origin
        and urlparse(origin).hostname not in ("localhost", "127.0.0.1", "[::1]", "::1")
    ):
        return Response("Local origin required", status_code=403)
    return await call_next(request)


@app.get("/health")
def health():
    with Session() as db:
        db.execute(text("SELECT 1"))
    return {"status": "healthy", "version": "0.2.0"}


class TaskInput(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), max_length=160, min_length=1)
    title: str = Field(default="Manual task", max_length=256)
    client_id: str = Field(default="unknown", max_length=80)
    client_version: str | None = None
    surface: str = Field(default="unknown", max_length=80)
    runtime: str = Field(default="unknown", max_length=80)
    integration_type: str = Field(default="api", max_length=80)
    workspace: str = Field(default="local", max_length=160)
    provider: str = Field(default="generic", max_length=80)
    account: str = Field(default="default", max_length=160)
    project: str = Field(default="unassigned", max_length=256)
    session_id: str = Field(default_factory=lambda: str(uuid4()), max_length=160)
    repository: str | None = Field(default=None, max_length=1024)
    git_branch: str | None = Field(default=None, max_length=256)
    git_commit_start: str | None = Field(default=None, max_length=128)
    source_surface: str = Field(default="generic-otel", max_length=80)
    started_at: str = Field(default_factory=utc)
    demo: bool = False


@app.post("/api/tasks", status_code=201)
def create_task(payload: TaskInput):
    with transaction() as db:
        if db.get(Task, payload.id):
            raise HTTPException(409, "Task ID exists")
        data = payload.model_dump()
        data.update(kind="manual", status="running", completed_at=None, trace_ids=[])
        db.add(
            Task(
                id=payload.id,
                client_id=payload.client_id,
                provider=payload.provider,
                session_id=payload.session_id,
                project=payload.project,
                started_at=utc(payload.started_at),
                data=data,
            )
        )
    return {"id": payload.id}


class CompleteInput(BaseModel):
    status: str = Field(default="completed", pattern="^(completed|failed|cancelled)$")
    completed_at: str = Field(default_factory=utc)
    git_commit_end: str | None = Field(default=None, max_length=128)


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, payload: CompleteInput):
    with transaction() as db:
        task = db.get(Task, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        if utc(payload.completed_at) < task.started_at:
            raise HTTPException(422, "Completion precedes task start")
        task.data = {**task.data, **payload.model_dump(), "completed_at": utc(payload.completed_at)}
    return {"id": task_id}


def store_snapshot(db, payload):
    data = payload.model_dump()
    data["id"] = payload.id or digest(data)
    for window in data["windows"]:
        window["remaining_percent"] = 100 - window["used_percent"]
    existing = db.get(Quota, data["id"])
    if existing:
        if existing.data != data:
            raise HTTPException(409, "Snapshot ID already contains different evidence")
        return existing.data
    db.add(
        Quota(
            id=data["id"],
            provider=data["provider"],
            account=data["account"],
            captured_at=data["captured_at"],
            data=data,
        )
    )
    return data


@app.post("/api/quota/snapshots", status_code=201)
def add_snapshot(payload: Snapshot):
    with transaction() as db:
        return store_snapshot(db, payload)


@app.post("/api/quota/statusline")
def statusline(payload: dict):
    try:
        snapshot = OfficialQuotaProvider().snapshot(payload=payload)
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(422, "No valid documented quota windows in payload") from exc
    with transaction() as db:
        store_snapshot(db, snapshot)
    return {"status": "recorded", "source": "official"}


@app.get("/api/quota")
def quotas(demo: bool | None = None, provider: str | None = None, account: str | None = None):
    with Session() as db:
        rows = db.scalars(select(Quota).order_by(Quota.captured_at.desc()).limit(1000)).all()
        return [
            q.data
            for q in rows
            if (demo is None or q.data["demo"] == demo)
            and (provider is None or q.provider == provider)
            and (account is None or q.account == account)
        ]


def ingest(records):
    count = 0
    with transaction() as db:
        catalogs, catalog_version = pricing.active_registry(db)
        for rec in records:
            if rec["kind"] == "metric":
                if not db.get(MetricObservation, rec["id"]) and not db.get(
                    MetricObservation, rec.get("legacy_id", rec["id"])
                ):
                    db.add(MetricObservation(id=rec["id"], timestamp=rec["timestamp"], data=rec))
                    db.flush()
                    count += 1
                continue
            existing = db.get(Event, rec["id"])
            if existing is None:
                legacy = db.get(Event, rec.get("legacy_id")) if rec.get("legacy_id") else None
                if (
                    legacy
                    and legacy.client_id in ("unknown", rec["client_id"])
                    and legacy.data.get("workspace", "local") == rec["workspace"]
                    and legacy.data.get("demo", False) == rec["demo"]
                ):
                    existing = legacy
            if existing is None and rec.get("trace_id") and rec.get("span_id"):
                # Older span identities included attributes. Enriching metadata must
                # not create a second event for the same execution span.
                candidates = db.scalars(
                    select(Event).where(
                        Event.provider == rec["provider"],
                        Event.kind == rec["kind"],
                        Event.timestamp == rec["timestamp"],
                        Event.client_id.in_(("unknown", rec["client_id"])),
                        Event.data["trace_id"].as_string() == rec["trace_id"],
                        Event.data["span_id"].as_string() == rec["span_id"],
                    )
                )
                existing = next(
                    (
                        candidate
                        for candidate in candidates
                        if candidate.data.get("session_id") == rec["session_id"]
                        and candidate.data.get("workspace", "local") == rec["workspace"]
                        and candidate.data.get("demo", False) == rec["demo"]
                    ),
                    None,
                )
            if existing:
                # A span may arrive after a log. Merge trace context without double-counting.
                merged = {**existing.data}
                for key in (
                    "trace_id",
                    "span_id",
                    "parent_span_id",
                    "agent_id",
                    "parent_agent_id",
                    "provider_emitted_cost",
                ):
                    if rec.get(key) is not None and rec.get(key) != "":
                        merged[key] = rec[key]
                if rec.get("agent_type") == "subagent":
                    merged.update(agent=rec["agent"], agent_type="subagent")
                merged["attrs"] = {**existing.data["attrs"], **rec["attrs"]}
                if existing.client_id == "unknown" and rec["client_id"] != "unknown":
                    existing.client_id = rec["client_id"]
                    merged.update(
                        {
                            k: rec[k]
                            for k in (
                                "client_id",
                                "client_version",
                                "surface",
                                "runtime",
                                "integration_type",
                                "workspace",
                            )
                        }
                    )
                existing.raw_attributes = {**(existing.raw_attributes or {}), **rec["raw_metadata"]}
                existing.normalized_attributes = rec["normalized_attributes"]
                existing.data = merged
                task = db.get(Task, existing.task_id)
                if task.client_id == "unknown" and rec["client_id"] != "unknown":
                    task.client_id = rec["client_id"]
                    task.data = {
                        **task.data,
                        **{
                            k: rec[k]
                            for k in (
                                "client_id",
                                "client_version",
                                "surface",
                                "runtime",
                                "integration_type",
                                "workspace",
                            )
                        },
                    }
                if rec["trace_id"] and rec["trace_id"] not in task.data.get("trace_ids", []):
                    task.data = {**task.data, "trace_ids": [*task.data.get("trace_ids", []), rec["trace_id"]]}
                continue
            attrs = rec["attrs"]
            explicit = attrs.get("tracequota.task.id")
            prompt = attrs.get("prompt.id")
            trace = rec["trace_id"]
            candidates = db.scalars(
                select(Task).where(
                    Task.session_id == rec["session_id"], Task.client_id.in_([rec["client_id"], "unknown"])
                )
            ).all()
            candidates = [t for t in candidates if t.data.get("workspace", "local") == rec["workspace"]]
            task = (
                db.get(Task, str(explicit))
                if explicit
                else next(
                    (
                        t
                        for t in candidates
                        if (prompt and prompt in t.data.get("prompt_ids", []))
                        or (trace and trace in t.data.get("trace_ids", []))
                    ),
                    None,
                )
            )
            kind = attrs.get(
                "tracequota.task.kind",
                "manual" if explicit else "interaction" if prompt or trace else "session_activity",
            )
            task_id = (
                str(explicit)
                if explicit
                else digest(rec["workspace"], rec["client_id"], rec["session_id"], "prompt", prompt)
                if prompt
                else digest(rec["workspace"], rec["client_id"], rec["session_id"], "trace", trace)
                if trace
                else digest(rec["workspace"], rec["client_id"], rec["session_id"], "session_activity")
            )
            if not task:
                task = db.get(Task, task_id)
            if task and (
                task.session_id != rec["session_id"]
                or task.client_id not in ("unknown", rec["client_id"])
                or task.data.get("workspace", "local") != rec["workspace"]
            ):
                raise HTTPException(409, "Task identity belongs to a different client/session")
            if not task:
                data = {
                    **{
                        k: rec[k]
                        for k in ("client_id", "client_version", "surface", "runtime", "integration_type", "workspace")
                    },
                    "title": attrs.get(
                        "tracequota.task.title",
                        "Interaction"
                        if kind == "interaction"
                        else "Session activity"
                        if kind == "session_activity"
                        else "Explicit task",
                    ),
                    "kind": kind,
                    "status": "running",
                    "completed_at": None,
                    "demo": rec["demo"],
                    "account": attrs.get("tracequota.account", "default"),
                    "trace_ids": [],
                    "prompt_ids": [],
                    "repository": attrs.get("vcs.repository.url.full", attrs.get("git.repository")),
                    "git_branch": attrs.get("vcs.ref.head.name", attrs.get("git.branch")),
                    "git_commit_start": attrs.get("vcs.ref.head.revision", attrs.get("git.commit")),
                    "source_surface": attrs.get(
                        "tracequota.source_surface",
                        attrs.get("source.surface", "claude-code" if rec["client_id"] == "claude_code" else "unknown"),
                    ),
                }
                task = Task(
                    id=task_id,
                    client_id=rec["client_id"],
                    provider=rec["provider"],
                    session_id=rec["session_id"],
                    project=str(
                        attrs.get(
                            "project.name",
                            attrs.get("tracequota.project", attrs.get("vcs.repository.name", "unassigned")),
                        )
                    ),
                    started_at=rec["timestamp"],
                    data=data,
                )
                db.add(task)
                db.flush()
            if task.client_id == "unknown" and rec["client_id"] != "unknown":
                task.client_id = rec["client_id"]
            session_key = digest(rec["workspace"], rec["client_id"], rec["session_id"])
            if not db.get(ExecutionSession, session_key):
                db.add(
                    ExecutionSession(
                        id=session_key,
                        client_id=rec["client_id"],
                        session_id=rec["session_id"],
                        data={
                            k: rec[k] for k in ("workspace", "client_version", "surface", "runtime", "integration_type")
                        },
                    )
                )
            agent_key = digest(task.id, rec.get("agent_id") or rec["agent"])
            if not db.get(AgentRun, agent_key):
                db.add(
                    AgentRun(
                        id=agent_key,
                        task_id=task.id,
                        agent_id=str(rec.get("agent_id") or rec["agent"]),
                        parent_agent_id=rec.get("parent_agent_id"),
                        data={"name": rec["agent"], "type": rec["agent_type"]},
                    )
                )
            if rec["kind"] == "llm":
                rec["pricing"] = pricing.calculate(
                    catalogs,
                    catalog_version,
                    rec["provider"],
                    rec["model_resolved"],
                    rec["usage"],
                    rec["timestamp"],
                    rec,
                )
                rec["estimated_api_equivalent_cost"] = rec["pricing"]["total"]
                rec["pricing_rule_id"] = rec["pricing"]["pricing_rule_id"]
                rec["pricing_catalog_version"] = rec["pricing"]["catalog_version"]
                rec["observed_provider_cost"] = rec["provider_emitted_cost"]
            task.started_at = min(task.started_at, rec["timestamp"])
            data = {**task.data}
            if trace and trace not in data.get("trace_ids", []):
                data["trace_ids"] = [*data.get("trace_ids", []), trace]
            if prompt and prompt not in data.get("prompt_ids", []):
                data["prompt_ids"] = [*data.get("prompt_ids", []), prompt]
            if rec["kind"] == "interaction" and rec["ended_at"]:
                data["completed_at"] = rec["ended_at"]
                data["status"] = attrs.get("tracequota.status", rec["status"])
            task.data = data
            db.add(
                Event(
                    id=rec["id"],
                    task_id=task.id,
                    timestamp=rec["timestamp"],
                    kind=rec["kind"],
                    client_id=rec["client_id"],
                    provider=rec["provider"],
                    model_id=rec["model_resolved"],
                    pricing_rule_id=(rec.get("pricing") or {}).get("pricing_rule_id"),
                    raw_attributes=rec["raw_metadata"],
                    normalized_attributes=rec["normalized_attributes"],
                    data=rec,
                )
            )
            db.flush()
            count += 1
    return count


async def decode_otlp(signal: str, request: Request):
    classes = {
        "traces": ExportTraceServiceRequest,
        "logs": ExportLogsServiceRequest,
        "metrics": ExportMetricsServiceRequest,
    }
    if signal not in classes:
        raise HTTPException(404, "Unknown OTLP signal")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 4 * 1024 * 1024:
            raise HTTPException(413, "OTLP batch exceeds 4 MiB")
    try:
        if request.headers.get("content-encoding") == "gzip":
            # Bounded decompression prevents small compressed requests exhausting memory.
            import io

            with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                body = gz.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise HTTPException(413, "Expanded batch exceeds 4 MiB")
        proto = "application/x-protobuf" in request.headers.get("content-type", "")
        if proto:
            message = classes[signal]()
            message.ParseFromString(bytes(body))
            payload = MessageToDict(message)
        else:
            payload = json.loads(body)
        return payload, proto
    except HTTPException:
        raise
    except Exception as exc:
        # Exporters retry transient database failures; malformed payloads are permanent errors.
        from sqlalchemy.exc import SQLAlchemyError

        if isinstance(exc, SQLAlchemyError):
            raise HTTPException(503, "Ledger temporarily unavailable") from exc
        raise HTTPException(400, "Invalid OTLP payload") from exc


@app.post("/v1/{signal}")
async def otlp(signal: str, request: Request):
    payload, proto = await decode_otlp(signal, request)
    try:
        ingest(normalise(payload, signal))
    except HTTPException:
        raise
    except Exception as exc:
        from sqlalchemy.exc import SQLAlchemyError

        raise HTTPException(
            503 if isinstance(exc, SQLAlchemyError) else 400,
            "Ledger unavailable" if isinstance(exc, SQLAlchemyError) else "Invalid OTLP metadata",
        ) from exc
    return Response(b"" if proto else "{}", media_type="application/x-protobuf" if proto else "application/json")


async def forward_phoenix(payload):
    import httpx

    message = ParseDict(sanitise_traces(payload), ExportTraceServiceRequest())
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            os.getenv("PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces"),
            content=message.SerializeToString(),
            headers={"Content-Type": "application/x-protobuf"},
        )
        response.raise_for_status()


@app.post("/phoenix/v1/traces")
async def phoenix_traces(request: Request):
    payload, proto = await decode_otlp("traces", request)
    try:
        await forward_phoenix(payload)
    except Exception as exc:
        raise HTTPException(503, "Phoenix temporarily unavailable") from exc
    return Response(b"" if proto else "{}", media_type="application/x-protobuf" if proto else "application/json")


def render_task(db, task, snapshots=None, filters=None):
    events = [e.data for e in db.scalars(select(Event).where(Event.task_id == task.id))]
    llms = [e for e in events if e["kind"] == "llm" and (not filters or filters.matches(e, task))]
    totals = {k: sum(e["tokens"][k] for e in llms) for k in CATEGORIES}
    agents, models = (
        defaultdict(lambda: dict.fromkeys(CATEGORIES, 0)),
        defaultdict(lambda: dict.fromkeys(CATEGORIES, 0)),
    )
    for e in llms:
        for k in CATEGORIES:
            agents[e["agent"]][k] += e["tokens"][k]
            models[e["model"]][k] += e["tokens"][k]
    snapshots = snapshots if snapshots is not None else [q.data for q in db.scalars(select(Quota))]
    matching = sorted(
        [
            q
            for q in snapshots
            if q["provider"] == task.provider
            and q["account"] == task.data.get("account", "default")
            and q["demo"] == task.data.get("demo", False)
            and (not q.get("session_id") or q["session_id"] == task.session_id)
            and (not q.get("task_id") or q["task_id"] == task.id)
        ],
        key=lambda q: q["captured_at"],
    )
    start = task.started_at
    end = task.data.get("completed_at")
    cutoff = utc(datetime.fromisoformat(start) - timedelta(hours=24))
    before = next((q for q in reversed(matching) if cutoff <= q["captured_at"] <= start), None)
    after_cutoff = utc(datetime.fromisoformat(end) + timedelta(minutes=15)) if end else None
    after = next((q for q in matching if end and end <= q["captured_at"] <= after_cutoff), None)
    result = {
        **task.data,
        "id": task.id,
        "provider": task.provider,
        "session_id": task.session_id,
        "project": task.project,
        "started_at": start,
        "tokens": totals,
        "total_token_activity": sum(totals.values()),
        **cost_summary(llms),
        "usage": usage_summary(llms),
        "client_id": task.client_id,
        "providers": sorted({e["provider"] for e in llms}),
        "quota_by_provider": quota_evidence(snapshots, task, {e["provider"] for e in llms} or {task.provider}),
        "provider_cost_kind": "provider-emitted estimate",
        "cost_currency": "USD",
        "agents": dict(agents),
        "models": dict(models),
        "main_agent_activity": sum(sum(e["tokens"].values()) for e in llms if e["agent_type"] == "main"),
        "subagent_activity": sum(sum(e["tokens"].values()) for e in llms if e["agent_type"] == "subagent"),
        "llm_calls": len(llms),
        "tool_calls": sum(e["kind"] in ("tool", "mcp") for e in events),
        "mcp_calls": sum(e["kind"] == "mcp" for e in events),
        "duration_seconds": max(0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())
        if end
        else None,
        "quota_before": before,
        "quota_after": after,
        "quota_delta": quota_delta(before, after),
        "last_telemetry_at": max((e["timestamp"] for e in events), default=None),
        "phoenix_trace_ids": task.data.get("trace_ids", []),
    }
    return result


@app.get("/api/tasks")
def tasks(
    project: str | None = None,
    model: str | None = None,
    agent: str | None = None,
    status: str | None = None,
    demo: bool | None = None,
    since: str | None = None,
    until: str | None = None,
    sort: str = "started_at",
    descending: bool = True,
    limit: int | None = 100,
    filters: Filters = Depends(),
):
    if not isinstance(filters, Filters):
        filters = Filters()
    filters = Filters(
        **{
            **vars(filters),
            **{
                k: v
                for k, v in {"project": project, "model": model, "agent": agent, "since": since, "until": until}.items()
                if v
            },
        }
    )
    if limit is not None and not 1 <= limit <= 1000:
        raise HTTPException(422, "Limit must be between 1 and 1000")
    with Session() as db:
        snapshots = [q.data for q in db.scalars(select(Quota))]
        query = select(Task).order_by(Task.started_at.desc())
        if project:
            query = query.where(Task.project == project)
        rows = [render_task(db, t, snapshots, filters) for t in db.scalars(query)]
        scoped = any(v for v in vars(filters).values())
        if scoped:
            rows = [t for t in rows if t["llm_calls"] > 0]
    rows = [
        t
        for t in rows
        if (not model or model in t["models"])
        and (not agent or agent in t["agents"])
        and (not status or t["status"] == status)
        and (demo is None or t["demo"] == demo)
    ]
    allowed = {
        "started_at",
        "project",
        "status",
        "total_token_activity",
        "estimated_api_cost",
        "duration_seconds",
        "quota_delta_pp",
    }
    if sort not in allowed:
        raise HTTPException(422, "Unsupported sort field")
    for row in rows:
        row["quota_delta_pp"] = next((q["delta_pp"] for q in row["quota_delta"] if q["name"] == "5h"), None)
    rows.sort(
        key=lambda t: (
            t.get(sort) is not None,
            Decimal(t.get(sort) or "0") if sort == "estimated_api_cost" else t.get(sort) or 0,
        ),
        reverse=descending,
    )
    return rows if limit is None else rows[:limit]


@app.get("/api/tasks/{task_id}")
def detail(task_id: str):
    with Session() as db:
        task = db.get(Task, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        result = render_task(db, task)
        result["events"] = [
            e.data for e in db.scalars(select(Event).where(Event.task_id == task.id).order_by(Event.timestamp))
        ]
        return result


@app.get("/api/overview")
def overview(demo: bool | None = None, filters: Filters = Depends()):
    if not isinstance(filters, Filters):
        filters = Filters()
    rows = tasks(demo=demo, limit=None, filters=filters)
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    week = (now.date() - timedelta(days=now.weekday())).isoformat()
    month = now.date().replace(day=1).isoformat()
    with Session() as db:
        pairs = db.execute(select(Event, Task).join(Task, Event.task_id == Task.id).where(Event.kind == "llm")).all()
        events = [
            {**e.data, "client_id": e.client_id, "project": t.project, "repository": t.data.get("repository")}
            for e, t in pairs
            if (demo is None or e.data["demo"] == demo) and filters.matches({**e.data, "client_id": e.client_id}, t)
        ]

    def period(since):
        selected = [e for e in events if e["timestamp"][:10] >= since]
        return {**cost_summary(selected), "token_activity": sum(sum(e["tokens"].values()) for e in selected)}

    costs = {}
    for field in ("client_id", "provider", "model", "project", "agent"):
        groups = defaultdict(list)
        for e in events:
            groups[e.get(field, "unknown")].append(e)
        costs[field] = {
            name: {
                **cost_summary(evs),
                "calls": len(evs),
                "token_activity": sum(sum(e["tokens"].values()) for e in evs),
            }
            for name, evs in groups.items()
        }
    return {
        "tokens_today": period(today)["token_activity"],
        "tokens_week": period(week)["token_activity"],
        "tasks_today": sum(t["started_at"][:10] == today for t in rows),
        "sessions": len({(t.get("workspace", "local"), t["client_id"], t["session_id"]) for t in rows}),
        "projects": len({t["project"] for t in rows}),
        "tasks": rows[:8],
        "quota": quotas(demo=demo, provider=filters.provider),
        "models": group_usage(rows, "models"),
        "agents": group_usage(rows, "agents"),
        "project_usage": group_usage(rows, "project"),
        "costs": costs,
        "cost_today": period(today),
        "cost_week": period(week),
        "cost_month": period(month),
        "usage": usage_summary(events),
        **cost_summary(events),
        "calculation": "API-equivalent workload estimate, not a subscription bill. Missing quantities remain unknown; legacy activity fields exclude unknown quantities.",
    }


@app.get("/api/filters")
def filter_options():
    with Session() as db:
        pairs = db.execute(select(Event, Task).join(Task, Event.task_id == Task.id).where(Event.kind == "llm")).all()
        result = defaultdict(set)
        for e, t in pairs:
            data = {
                **t.data,
                **e.data,
                "client": e.client_id,
                "project": t.project,
                "repository": t.data.get("repository"),
                "pricing_confidence": (e.data.get("pricing") or {}).get(
                    "confidence", "legacy" if (e.data.get("pricing") or {}).get("usd") is not None else "unknown"
                ),
            }
            for key in vars(Filters()):
                if key not in ("since", "until") and data.get(key):
                    result[key].add(str(data[key]))
        return {k: sorted(v) for k, v in result.items()}


@app.get("/api/pricing/status")
def pricing_status():
    with Session() as db:
        return pricing.status(db)


@app.post("/api/pricing/sync")
def pricing_sync():
    try:
        with transaction() as db:
            return pricing.sync(db)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/pricing/rules")
def pricing_rules():
    with Session() as db:
        catalogs, version = pricing.active_registry(db)
        return {"catalog_version": version, "catalogs": [c.model_dump(mode="json") for c in catalogs]}


def group_usage(rows, field):
    result = defaultdict(int)
    for task in rows:
        if field == "project":
            result[task[field]] += task["total_token_activity"]
        else:
            for name, tokens in task[field].items():
                result[name] += sum(tokens.values())
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


@app.get("/api/sessions")
def sessions(demo: bool | None = None, filters: Filters = Depends()):
    rows = tasks(demo=demo, limit=None, filters=filters)
    groups = {}
    for task in rows:
        key = task.get("workspace", "local") + ":" + task["client_id"] + ":" + task["session_id"]
        g = groups.setdefault(
            key,
            {
                "id": task["session_id"],
                "client_id": task["client_id"],
                "client_version": task.get("client_version"),
                "surface": task.get("surface", "unknown"),
                "runtime": task.get("runtime", "unknown"),
                "integration_type": task.get("integration_type", "unknown"),
                "providers": [],
                "estimated_api_equivalent_cost": "0",
                "priced_partial_cost": None,
                "unpriced_requests": 0,
                "provider": task["provider"],
                "project": task["project"],
                "tasks": 0,
                "tokens": 0,
                "demo": task["demo"],
            },
        )
        g["tasks"] += 1
        g["tokens"] += task["total_token_activity"]
        g["providers"] = sorted(set(g["providers"]) | set(task["providers"]))
        g["unpriced_requests"] += task["unpriced_requests"]
        g["priced_partial_cost"] = (
            str(Decimal(g["priced_partial_cost"] or "0") + Decimal(task["priced_partial_cost"] or "0"))
            if g["priced_partial_cost"] is not None or task["priced_partial_cost"] is not None
            else None
        )
        g["estimated_api_equivalent_cost"] = g["priced_partial_cost"] if g["unpriced_requests"] == 0 else None
    return list(groups.values())


@app.get("/api/projects")
def projects(demo: bool | None = None, filters: Filters = Depends()):
    rows = tasks(demo=demo, limit=None, filters=filters)
    return [
        {
            "name": name,
            "tokens": amount,
            "tasks": sum(t["project"] == name for t in rows),
            "estimated_api_equivalent_cost": str(
                sum((Decimal(t["estimated_api_equivalent_cost"]) for t in rows if t["project"] == name), Decimal(0))
            )
            if all(t["estimated_api_equivalent_cost"] is not None for t in rows if t["project"] == name)
            else None,
        }
        for name, amount in group_usage(rows, "project").items()
    ]


@app.get("/api/integrations")
def integrations():
    with Session() as db:
        observations = [e.data for e in db.scalars(select(Event).order_by(Event.timestamp.desc()).limit(1000))]
        metric_count = len(db.scalars(select(MetricObservation.id)).all())
    return {
        "clients": [
            {
                **descriptor,
                "last_seen": next(
                    (e["timestamp"] for e in observations if e.get("client_id") == descriptor["id"] and not e["demo"]),
                    None,
                ),
                "demo_seen": any(e.get("client_id") == descriptor["id"] and e["demo"] for e in observations),
            }
            for descriptor in clients.descriptors()
        ],
        "claude_code": {
            "support": "official metrics/events; beta traces",
            "last_seen": next(
                (e["timestamp"] for e in observations if e.get("client_id") == "claude_code" and not e["demo"]), None
            ),
        },
        "generic_otlp": {
            "support": "OTLP HTTP/protobuf and JSON via Collector",
            "last_seen": next((e["timestamp"] for e in observations if not e["demo"]), None),
        },
        "desktop_code_local": {"support": "documented configuration; live runtime unverified"},
        "quota": {
            "support": "manual, explicit estimates, official status-line adapter",
            "experimental": "disabled; no network collector implemented",
        },
        "metrics_observations": metric_count,
        "content_capture": False,
    }


@app.get("/api/settings")
def settings():
    return {
        "privacy_mode": "metadata only",
        "rich_capture": "requires an explicit custom Collector configuration",
        "links": {
            "grafana": os.getenv("GRAFANA_PUBLIC_URL", "http://localhost:3000"),
            "phoenix": os.getenv("PHOENIX_PUBLIC_URL", "http://localhost:6006"),
        },
        "pricing_version": "2026-09-28",
        "pricing": pricing_status(),
        "timezone": "UTC",
        "retention": "until local volumes are explicitly deleted",
        "quota_attribution": "Account window deltas are not isolated causal task usage.",
    }


@app.post("/api/hooks/claude")
def hook(payload: dict):
    # HTTP hook bodies can contain prompt and transcript fields. Persist none of them.
    event = payload.get("hook_event_name")
    session = str(payload.get("session_id", "unknown"))[:160]
    if event == "SessionStart":
        ident = digest("anthropic", session, "session_activity")
        with transaction() as db:
            if not db.get(Task, ident):
                db.add(
                    Task(
                        id=ident,
                        client_id="claude_code",
                        provider="anthropic",
                        session_id=session,
                        project="unassigned",
                        started_at=utc(),
                        data={
                            "title": "Session activity",
                            "kind": "session_activity",
                            "status": "running",
                            "completed_at": None,
                            "demo": False,
                            "trace_ids": [],
                            "source_surface": "claude-code",
                            "account": "default",
                        },
                    )
                )
    elif event == "SessionEnd":
        with transaction() as db:
            for task in db.scalars(select(Task).where(Task.provider == "anthropic", Task.session_id == session)):
                if task.data.get("kind") == "session_activity":
                    task.data = {**task.data, "completed_at": utc(), "status": "completed"}
    return {}  # Claude-compatible non-blocking response; never makes agent decisions.


@app.get("/metrics")
def metrics():
    rows = tasks(limit=None)
    lines = [
        "# HELP tracequota_token_activity Metadata-only request ledger token activity.",
        "# TYPE tracequota_token_activity gauge",
    ]

    def labels(**kw):
        return ",".join(k + "=" + json.dumps(str(v)) for k, v in kw.items())

    for field in CATEGORIES:
        for demo in (False, True):
            lines.append(
                f"tracequota_token_activity{{{labels(category=field, demo=str(demo).lower())}}} {sum(t['tokens'][field] for t in rows if t['demo'] == demo)}"
            )
    with Session() as db:
        aggregates = defaultdict(int)
        confidence_counts = defaultdict(int)
        cost_groups = defaultdict(lambda: Decimal(0))
        for event in db.scalars(select(Event).where(Event.kind == "llm")):
            data = event.data
            dims = (event.client_id, event.provider, str(data.get("demo", False)).lower())
            for category, quantity in data["tokens"].items():
                aggregates[(*dims, category)] += quantity
            p = data.get("pricing") or {}
            confidence_counts[(*dims, p.get("confidence", "legacy" if p.get("usd") is not None else "unknown"))] += 1
            part = p.get("partial_total", p.get("usd"))
            if part is not None:
                cost_groups[dims] += Decimal(str(part))
        for (client_id, provider, demo, category), quantity in aggregates.items():
            lines.append(
                f"tracequota_client_token_activity{{{labels(client=client_id, provider=provider, demo=demo, category=category)}}} {quantity}"
            )
        for (client_id, provider, demo, confidence), quantity in confidence_counts.items():
            lines.append(
                f"tracequota_model_calls{{{labels(client=client_id, provider=provider, demo=demo, confidence=confidence)}}} {quantity}"
            )
        for (client_id, provider, demo), amount in cost_groups.items():
            lines.append(
                f"tracequota_priced_partial_usd{{{labels(client=client_id, provider=provider, demo=demo)}}} {amount}"
            )
    lines.append(f"tracequota_tasks {len(rows)}")
    lines.append(f"tracequota_sessions {len({(t['provider'], t['session_id']) for t in rows})}")
    for q in quotas()[:100]:
        for w in q["windows"]:
            lines.append(
                f"tracequota_quota_used_percent{{{labels(snapshot=q['id'], provider=q['provider'], account=q['account'], window=w['name'], source=q['source'], demo=str(q['demo']).lower())}}} {w['used_percent']}"
            )
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


class EstimateInput(BaseModel):
    used_units: float = Field(ge=0)
    capacity: float = Field(gt=0)
    account: str = Field(default="default", max_length=160)
    provider: str = Field(default="anthropic", max_length=80)
    window: str = Field(default="5h", max_length=80)


@app.post("/api/quota/estimate", status_code=201)
def estimated_quota(payload: EstimateInput):
    from .domain import EstimatedQuotaProvider

    snapshot = EstimatedQuotaProvider().snapshot(**payload.model_dump())
    with transaction() as db:
        result = store_snapshot(db, snapshot)
        result["estimation_basis"] = {"used_units": payload.used_units, "capacity": payload.capacity}
        db.flush()
        row = db.get(Quota, result["id"])
        row.data = result
        return result


@app.get("/api/metrics/observations")
def metric_observations():
    with Session() as db:
        return [
            e.data
            for e in db.scalars(select(MetricObservation).order_by(MetricObservation.timestamp.desc()).limit(1000))
        ]
