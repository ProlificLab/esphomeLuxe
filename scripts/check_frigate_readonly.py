#!/usr/bin/env python3
"""Enforce the static security contract of the Frigate HA integration."""

from __future__ import annotations

import argparse
from pathlib import Path


PINNED_VERSION = "5.15.4"
PINNED_COMMIT = "7c5aea2d46d5d3c96a6adce57e0b71c42ccfba25"
PINNED_SHA256 = "deab640ef1c50c74db4ba4879694daf6941fc587c2a6109d43e6cfea1be62f2a"


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing {label}: {marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    provision = (args.root / "scripts/provision_frigate_readonly.sh").read_text()
    configure = (args.root / "scripts/configure_frigate_integration.py").read_text()
    harden = (args.root / "scripts/harden_frigate_readonly.py").read_text()
    viewer = (args.root / "frigate/provision_viewer.py").read_text()
    live_test = (args.root / "scripts/test_frigate_viewer.sh").read_text()

    for source in (provision, configure, live_test):
        require(source, "http://192.168.1.20:8971", "authenticated Frigate endpoint")
        if "192.168.1.20:5000" in source:
            raise RuntimeError("The unauthenticated Frigate port 5000 is forbidden")

    require(provision, f'INTEGRATION_VERSION="{PINNED_VERSION}"', "integration pin")
    require(provision, f'INTEGRATION_COMMIT="{PINNED_COMMIT}"', "commit pin")
    require(provision, f'INTEGRATION_SHA256="{PINNED_SHA256}"', "archive checksum")
    require(provision, "shasum -a 256 -c -", "checksum verification")
    require(configure, 'default="homeassistant_muse"', "dedicated HA identity")
    require(viewer, '"role": "viewer"', "viewer attestation")
    require(viewer, "role = 'viewer'", "viewer database role")
    require(
        harden,
        'CONTROL_DOMAINS = {"button", "number", "select", "switch"}',
        "control allowlist",
    )
    require(harden, '"should_expose": False', "raw Assist isolation")
    require(harden, 'payload["disabled_by"] = "user"', "control disabling")
    require(live_test, '.role == "viewer"', "live viewer assertion")
    require(live_test, '[[ "$admin_code" == "403" ]]', "admin denial assertion")

    print("Frigate read-only security contract passed.")


if __name__ == "__main__":
    main()
