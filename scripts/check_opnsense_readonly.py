#!/usr/bin/env python3
"""Reject an OPNsense companion endpoint with broader-than-read-only scope."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


EXPECTED_PRIVILEGE = "page-muse-readonly"
EXPECTED_PATTERN = "api/muse/status/gateways"
FORBIDDEN_CONTROLLER_MARKERS = (
    "configdpRun",
    "serializeToConfig",
    "setAction",
    "addAction",
    "delAction",
    "save(",
)


def validate(controller: str, acl_root: ET.Element) -> None:
    privileges = list(acl_root)
    if len(privileges) != 1 or privileges[0].tag != EXPECTED_PRIVILEGE:
        raise ValueError("ACL must contain only the dedicated Muse privilege")
    patterns = [node.text or "" for node in privileges[0].findall("./patterns/pattern")]
    if patterns != [EXPECTED_PATTERN]:
        raise ValueError("ACL pattern must match only the exact telemetry endpoint")
    if "isGet()" not in controller:
        raise ValueError("Controller must explicitly reject non-GET requests")
    if "configdRun('interface gateways status')" not in controller:
        raise ValueError("Controller must use only the gateway status backend action")
    forbidden = [marker for marker in FORBIDDEN_CONTROLLER_MARKERS if marker in controller]
    if forbidden:
        raise ValueError(f"Mutable controller primitive found: {', '.join(forbidden)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("controller", type=Path)
    parser.add_argument("acl", type=Path)
    args = parser.parse_args()
    validate(
        args.controller.read_text(encoding="utf-8"),
        ET.parse(args.acl).getroot(),
    )
    print("OPNsense companion policy passed: one exact GET-only telemetry endpoint.")


if __name__ == "__main__":
    main()
