#!/usr/bin/env python3
"""Verify that a reviewed USB factory image embeds the exact hal.6 OTA."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from check_rollback_artifact import validate_rollback


HAL6_OTA_SHA256 = "8a8350fa93293ef8421f4c84004c4804a2969ae6d50697a72e104ba85d4db0d6"
HAL6_FACTORY_SHA256 = "16ad19ae504dae9e75d6be0cb72b6ada34bf932fae0f972a89b5230dc20c01ac"
APP_OFFSET = 0x10000


def regular_bytes(path: Path, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} must be a regular non-symlink file")
    data = path.read_bytes()
    if not data:
        raise RuntimeError(f"{label} must not be empty")
    return data


def validate_usb_recovery(
    ota_path: Path,
    factory_path: Path,
    manifest_path: Path,
) -> dict[str, object]:
    ota = regular_bytes(ota_path, "hal.6 OTA image")
    factory = regular_bytes(factory_path, "hal.6 factory image")
    if hashlib.sha256(ota).hexdigest() != HAL6_OTA_SHA256:
        raise RuntimeError("OTA image differs from the immutable hal.6 SHA-256")
    validate_rollback(ota_path, manifest_path, HAL6_OTA_SHA256)

    factory_sha256 = hashlib.sha256(factory).hexdigest()
    if factory_sha256 != HAL6_FACTORY_SHA256:
        raise RuntimeError("Factory image differs from the canonical hal.6 SHA-256")
    if len(factory) != APP_OFFSET + len(ota):
        raise RuntimeError("Factory image has an unexpected layout or trailing data")
    if (
        factory[0x1000:0x1001] != b"\xe9"
        or factory[0x8000:0x8002] != b"\xaa\x50"
        or ota[:1] != b"\xe9"
    ):
        raise RuntimeError("Factory bootloader, partition or OTA marker is invalid")
    if factory[APP_OFFSET:] != ota:
        raise RuntimeError("Factory image does not embed the exact hal.6 OTA at 0x10000")

    return {
        "schema_version": 1,
        "passed": True,
        "version": "2025.3.1-hal.6",
        "app_offset": APP_OFFSET,
        "ota_bytes": len(ota),
        "ota_sha256": HAL6_OTA_SHA256,
        "factory_bytes": len(factory),
        "factory_sha256": factory_sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ota", type=Path)
    parser.add_argument("factory", type=Path)
    parser.add_argument("--manifest", type=Path, default="manifest_update.json")
    args = parser.parse_args()
    result = validate_usb_recovery(args.ota, args.factory, args.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
