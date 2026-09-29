# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Read-only upstream multi-architecture manifest check; no Docker daemon needed."""

from pathlib import Path

import httpx
import yaml

root = Path(__file__).parents[1]
images = {
    s["image"]
    for s in yaml.safe_load((root / "docker-compose.yml").read_text())["services"].values()
    if not s["image"].startswith("tracequota-")
}
images |= {"python:3.12.11-slim-bookworm", "node:24.14.0-alpine", "nginxinc/nginx-unprivileged:1.28.0-alpine"}
with httpx.Client(timeout=40) as client:
    for image in sorted(images):
        repo, tag = image.rsplit(":", 1)
        if "/" not in repo:
            repo = "library/" + repo
        token = client.get(
            "https://auth.docker.io/token", params={"service": "registry.docker.io", "scope": f"repository:{repo}:pull"}
        ).json()["token"]
        r = client.get(
            f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json",
            },
        )
        r.raise_for_status()
        platforms = {
            m.get("platform", {}).get("architecture")
            for m in r.json().get("manifests", [])
            if m.get("platform", {}).get("os") == "linux"
        }
        assert {"amd64", "arm64"} <= platforms, (image, platforms)
        print(f"PASS {image}: linux/amd64 + linux/arm64")
