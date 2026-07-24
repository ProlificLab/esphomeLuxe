#!/usr/bin/env python3
"""Compose the canonical hal.6 USB image from a pinned prefix and exact OTA."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from check_rollback_artifact import validate_rollback


APP_OFFSET = 0x10000
HAL6_OTA_SHA256 = "8a8350fa93293ef8421f4c84004c4804a2969ae6d50697a72e104ba85d4db0d6"
HAL6_PREFIX_SHA256 = "845bf05b4e85a991d0f79f397172d10e538c1d903f76623bc1a17e74c4733656"
HAL6_FACTORY_SHA256 = "16ad19ae504dae9e75d6be0cb72b6ada34bf932fae0f972a89b5230dc20c01ac"


def regular_bytes(path: Path, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} must be a regular non-symlink file")
    data = path.read_bytes()
    if not data:
        raise RuntimeError(f"{label} must not be empty")
    return data


def compose(
    ota_path: Path,
    donor_factory_path: Path,
    manifest_path: Path,
    output_path: Path,
) -> dict[str, object]:
    if output_path.exists() or output_path.is_symlink():
        raise RuntimeError("Recovery output already exists; refusing to overwrite")
    if not output_path.parent.is_dir() or output_path.parent.is_symlink():
        raise RuntimeError("Recovery output parent must be a regular directory")

    ota = regular_bytes(ota_path, "hal.6 OTA image")
    donor = regular_bytes(donor_factory_path, "historical donor factory image")
    if hashlib.sha256(ota).hexdigest() != HAL6_OTA_SHA256:
        raise RuntimeError("OTA image differs from the immutable hal.6 SHA-256")
    validate_rollback(ota_path, manifest_path, HAL6_OTA_SHA256)
    if len(donor) <= APP_OFFSET or donor[APP_OFFSET : APP_OFFSET + 1] != b"\xe9":
        raise RuntimeError("Historical donor lacks an ESP32 application at 0x10000")

    prefix = donor[:APP_OFFSET]
    if hashlib.sha256(prefix).hexdigest() != HAL6_PREFIX_SHA256:
        raise RuntimeError("Historical donor prefix differs from the reviewed SHA-256")
    if prefix[0x1000:0x1001] != b"\xe9" or prefix[0x8000:0x8002] != b"\xaa\x50":
        raise RuntimeError("Historical donor bootloader or partition marker is invalid")

    factory = prefix + ota
    if hashlib.sha256(factory).hexdigest() != HAL6_FACTORY_SHA256:
        raise RuntimeError("Composed factory differs from the canonical SHA-256")

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(factory)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.chmod(temporary_name, 0o600)
        os.link(temporary_name, output_path)
        os.unlink(temporary_name)
        temporary_name = None
        directory_fd = os.open(output_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    return {
        "schema_version": 1,
        "passed": True,
        "version": "2025.3.1-hal.6",
        "app_offset": APP_OFFSET,
        "prefix_sha256": HAL6_PREFIX_SHA256,
        "ota_sha256": HAL6_OTA_SHA256,
        "factory_sha256": HAL6_FACTORY_SHA256,
        "factory_bytes": len(factory),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ota", type=Path)
    parser.add_argument("donor_factory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path, default="manifest_update.json")
    args = parser.parse_args()
    result = compose(args.ota, args.donor_factory, args.manifest, args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
