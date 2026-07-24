#!/usr/bin/env python3
"""Require the active secrets to match the immutable hal.6 credential domain."""

from __future__ import annotations

import argparse
import hmac
import json
import os
from pathlib import Path

import yaml


REQUIRED_KEYS = ("api_encryption_key", "ota_password", "fallback_ap_password")
EXAMPLE_VALUES = {
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    "replace-with-a-long-random-password",
    "replace-with-random",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def load(path: Path, *, private: bool) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        fail("Credential input must be a regular non-symlink file")
    if private:
        metadata = path.stat()
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            fail("Active credential file must be current-user private")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("Credential input must be a YAML mapping")
    result: dict[str, str] = {}
    for key in REQUIRED_KEYS:
        item = value.get(key)
        if not isinstance(item, str) or len(item) < 8:
            fail(f"Credential input is missing {key}")
        result[key] = item
    return result


def validate(active_path: Path, reference_path: Path) -> dict[str, object]:
    active = load(active_path, private=True)
    reference = load(reference_path, private=True)
    if any(value in EXAMPLE_VALUES for value in reference.values()):
        fail("Immutable hal.6 reference contains example credentials; use USB recovery")
    comparisons = (
        hmac.compare_digest(active[key].encode(), reference[key].encode())
        for key in REQUIRED_KEYS
    )
    compatible = all(tuple(comparisons))
    if not compatible:
        fail("Active credentials do not match immutable hal.6; use USB recovery")
    return {
        "schema_version": 1,
        "passed": True,
        "target_version": "2025.3.1-hal.6",
        "credential_keys_matched": len(REQUIRED_KEYS),
        "ota_safe": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("active_secrets", type=Path)
    parser.add_argument("hal6_reference", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.active_secrets, args.hal6_reference), sort_keys=True))


if __name__ == "__main__":
    main()
