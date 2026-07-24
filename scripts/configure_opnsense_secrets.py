#!/usr/bin/env python3
"""Atomically install OPNsense API credentials in Home Assistant secrets."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


KEYS = ("opnsense_muse_api_key", "opnsense_muse_api_secret")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets", type=Path, default=Path("/config/secrets.yaml"))
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--secret-file", type=Path, required=True)
    return parser.parse_args()


def yaml_scalar(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> None:
    args = parse_args()
    try:
        api_key = args.key_file.read_text(encoding="utf-8").strip()
        api_secret = args.secret_file.read_text(encoding="utf-8").strip()
        if not api_key or not api_secret or "\n" in api_key or "\n" in api_secret:
            raise RuntimeError("Invalid OPNsense credential input")

        current = args.secrets.read_text(encoding="utf-8") if args.secrets.exists() else ""
        pattern = re.compile(rf"^(?:{'|'.join(map(re.escape, KEYS))}):.*(?:\n|$)", re.MULTILINE)
        current = pattern.sub("", current).rstrip() + "\n"
        current += f"{KEYS[0]}: {yaml_scalar(api_key)}\n"
        current += f"{KEYS[1]}: {yaml_scalar(api_secret)}\n"

        temporary = args.secrets.with_suffix(".yaml.muse-new")
        temporary.write_text(current, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, args.secrets)
        print("OPNsense Home Assistant secrets installed")
    finally:
        for path in (args.key_file, args.secret_file):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()
