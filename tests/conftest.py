# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracequota import db, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = os.getenv("TEST_DATABASE_URL", "sqlite:///" + str(tmp_path / "ledger.db"))
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    db.Base.metadata.drop_all(engine)
    db.Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "Session", factory)
    monkeypatch.setattr(main, "Session", factory)
    with TestClient(main.app) as client:
        yield client
    engine.dispose()
