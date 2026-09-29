# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

from alembic import context
from tracequota.db import Base, engine

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
