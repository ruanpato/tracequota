# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Exercise provisioned datasources through Grafana, including macro expansion."""

import time


def check_grafana(client, url, password="tracequota-local"):
    auth = ("local", password)
    dashboard = client.get(url + "/api/dashboards/uid/tracequota").json()["dashboard"]
    checked = 0
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            query = {**target, "datasource": panel["datasource"], "intervalMs": 10000, "maxDataPoints": 500}
            if "rawSql" in query:
                query["rawSql"] = query["rawSql"].replace("${data}", "demo")
                for dimension in ("client", "provider", "model", "project", "agent"):
                    query["rawSql"] = query["rawSql"].replace("${" + dimension + ":sqlstring}", "'__all'")
            else:
                query.update(instant=True, range=False)
            response = client.post(
                url + "/api/ds/query",
                auth=auth,
                json={
                    "from": str(int((time.time() - 604800) * 1000)),
                    "to": str(int(time.time() * 1000)),
                    "queries": [query],
                },
            )
            response.raise_for_status()
            result = response.json()["results"][query["refId"]]
            assert result.get("status") == 200 and not result.get("error"), (panel["title"], result)
            checked += 1
    assert checked >= 23
    print(f"PASS: {checked} provisioned panels queried through Grafana's datasources.")
    return {"grafana_panels_queried": checked, "data_mode": "demo"}
