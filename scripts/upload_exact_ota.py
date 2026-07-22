#!/usr/bin/env python3
"""Upload one exact OTA artifact with ESPHome's pinned OTA implementation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml
from esphome.espota2 import run_ota


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=3232)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--secrets", type=Path, required=True)
    args = parser.parse_args()

    if not args.artifact.is_file() or args.artifact.stat().st_size == 0:
        raise SystemExit("OTA artifact is missing or empty")
    secrets = yaml.safe_load(args.secrets.read_text(encoding="utf-8"))
    password = secrets.get("ota_password") if isinstance(secrets, dict) else None
    if not isinstance(password, str) or len(password) < 16:
        raise SystemExit("ota_password is missing or shorter than 16 characters")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    status, _ = run_ota(args.host, args.port, password, args.artifact)
    if status != 0:
        raise SystemExit(status)


if __name__ == "__main__":
    main()
