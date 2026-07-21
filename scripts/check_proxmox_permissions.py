#!/usr/bin/env python3
"""Verify a Proxmox effective-permissions JSON document is audit-only."""

from __future__ import annotations

import json
import sys


REQUIRED = {"Sys.Audit", "VM.Audit"}


def validate(document: dict) -> set[str]:
    granted = {
        privilege
        for privileges in document.values()
        if isinstance(privileges, dict)
        for privilege, value in privileges.items()
        if value == 1
    }
    if missing := REQUIRED - granted:
        raise ValueError(f"Missing required audit privileges: {sorted(missing)}")
    if forbidden := {item for item in granted if not item.endswith(".Audit")}:
        raise ValueError(f"Non-audit privileges granted: {sorted(forbidden)}")
    return granted


def main() -> None:
    document = json.load(sys.stdin)
    granted = validate(document)
    print(f"Proxmox permissions passed: {len(granted)} unique audit privileges.")


if __name__ == "__main__":
    main()
