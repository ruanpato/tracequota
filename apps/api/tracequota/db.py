# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import os
from contextlib import contextmanager

from sqlalchemy import JSON, ForeignKey, String, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tracequota.db")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(80), index=True, default="unknown")
    provider: Mapped[str] = mapped_column(String(80), index=True)
    session_id: Mapped[str] = mapped_column(String(160), index=True)
    project: Mapped[str] = mapped_column(String(256), index=True)
    started_at: Mapped[str] = mapped_column(String(40), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    client_id: Mapped[str] = mapped_column(String(80), index=True, default="unknown")
    provider: Mapped[str] = mapped_column(String(80), index=True, default="unknown")
    model_id: Mapped[str] = mapped_column(String(160), index=True, default="unknown")
    pricing_rule_id: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    raw_attributes: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    normalized_attributes: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    data: Mapped[dict] = mapped_column(JSON)


class Quota(Base):
    __tablename__ = "quota_snapshots"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    account: Mapped[str] = mapped_column(String(160), index=True)
    captured_at: Mapped[str] = mapped_column(String(40), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class MetricObservation(Base):
    __tablename__ = "metric_observations"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    data: Mapped[dict] = mapped_column(JSON)


@contextmanager
def transaction():
    with Session.begin() as db:
        # Serialize ledger writes, including deduplication, across API workers.
        if engine.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(782417)"))
        yield db


class ExecutionSession(Base):
    __tablename__ = "execution_sessions"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(80), index=True)
    session_id: Mapped[str] = mapped_column(String(160), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(160), index=True)
    parent_agent_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)


class CatalogVersion(Base):
    __tablename__ = "catalog_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    imported_at: Mapped[str] = mapped_column(String(40))
    last_synced_at: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(default=False)
    data: Mapped[list] = mapped_column(JSON)


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    catalog_version: Mapped[str] = mapped_column(ForeignKey("catalog_versions.id"), index=True)
    rule_id: Mapped[str] = mapped_column(String(200), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    model_id: Mapped[str] = mapped_column(String(160), index=True)
    data: Mapped[dict] = mapped_column(JSON)
