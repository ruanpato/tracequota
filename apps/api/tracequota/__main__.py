# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

import argparse
import json

from . import pricing
from .db import Session, transaction


def main():
    parser = argparse.ArgumentParser(prog="python -m tracequota")
    parser.add_argument("area", choices=["pricing"])
    parser.add_argument("command", choices=["validate", "sync", "status"])
    args = parser.parse_args()
    if args.command == "validate":
        catalogs, version = pricing.load_registry()
        result = {
            "valid": True,
            "catalog_version": version,
            "providers": len(catalogs),
            "rules": sum(len(c.rules) for c in catalogs),
        }
    elif args.command == "sync":
        with transaction() as db:
            result = pricing.sync(db)
    else:
        with Session() as db:
            result = pricing.status(db)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
