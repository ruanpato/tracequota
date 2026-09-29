# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Execute provisioned dashboard SQL after migrations, without requiring Grafana."""

import json
import os
import re
from pathlib import Path

from sqlalchemy import create_engine, text


def check(database_url):
    dashboard = json.loads((Path(__file__).parents[1] / "dashboards/tracequota.json").read_text())
    count = 0
    with create_engine(database_url).connect() as connection:
        for mode in ("all", "demo", "live"):
            for panel in dashboard["panels"]:
                for target in panel.get("targets", []):
                    if "rawSql" not in target:
                        continue
                    query = target["rawSql"].replace("${data}", mode)
                    for dimension in ("client", "provider", "model", "project", "agent"):
                        query = query.replace("${" + dimension + ":sqlstring}", "'__all'")
                    query = re.sub(
                        r"\$__timeFilter\((.*?)\)",
                        lambda match: match[1] + " >= now()-interval '7 days'",
                        query,
                    )
                    query = query.replace("$__timeGroupAlias(time,'1h')", "date_trunc('hour', time) AS time")
                    connection.execute(text(query)).all()
                    count += 1
    print(f"PASS: {count} PostgreSQL dashboard queries across all/demo/live.")


if __name__ == "__main__":
    check(os.environ["DATABASE_URL"])
