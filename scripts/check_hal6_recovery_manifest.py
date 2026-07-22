#!/usr/bin/env python3
"""Validate the public provenance record for canonical hal.6 USB recovery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from check_hal6_usb_recovery import (
    APP_OFFSET,
    HAL6_FACTORY_SHA256 as CHECKED_FACTORY_SHA256,
    HAL6_OTA_SHA256 as CHECKED_OTA_SHA256,
)
from compose_hal6_usb_recovery import (
    HAL6_FACTORY_SHA256,
    HAL6_OTA_SHA256,
    HAL6_PREFIX_SHA256,
)


EXPECTED = {
    "schema_version": 1,
    "version": "2025.3.1-hal.6",
    "source": {
        "firmware_commit": "6f5b3a93320380a50a910376491d1c7381ba1fc8",
        "ci_commit": "63c89e723f4175a2fc79fda922dcfd8eef5f2f7b",
        "esphome_image": (
            "esphome/esphome@sha256:"
            "def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
        ),
    },
    "layout": {
        "bootloader_offset": 0x1000,
        "partition_table_offset": 0x8000,
        "ota_data_offset": 0xD000,
        "app_offset": APP_OFFSET,
    },
    "artifacts": {
        "ota": {
            "bytes": 1_948_144,
            "md5": "cedf966640caccbabba098bcf22f7645",
            "sha256": HAL6_OTA_SHA256,
        },
        "prefix": {"bytes": APP_OFFSET, "sha256": HAL6_PREFIX_SHA256},
        "factory": {"bytes": 2_013_680, "sha256": HAL6_FACTORY_SHA256},
    },
}


def validate(path: Path, root: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Recovery provenance must be a regular non-symlink file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value != EXPECTED:
        raise RuntimeError("Recovery provenance differs from the closed schema or values")
    if HAL6_OTA_SHA256 != CHECKED_OTA_SHA256 or HAL6_FACTORY_SHA256 != CHECKED_FACTORY_SHA256:
        raise RuntimeError("Composer and checker recovery identities differ")

    release_manifest = json.loads((root / "manifest_update.json").read_text(encoding="utf-8"))
    ota_manifest = release_manifest["builds"][0]["ota"]
    if (
        release_manifest.get("version") != EXPECTED["version"]
        or ota_manifest.get("md5") != EXPECTED["artifacts"]["ota"]["md5"]
        or ota_manifest.get("offset") != 0
    ):
        raise RuntimeError("Immutable OTA manifest differs from recovery provenance")

    partitions = (root / "luxe_partitions.csv").read_text(encoding="utf-8")
    if "app0,       app,  ota_0,   0x10000,  0x1F0000," not in partitions:
        raise RuntimeError("Partition table no longer places app0 at 0x10000")
    workflow = (root / ".github/workflows/firmware.yml").read_text(encoding="utf-8")
    if EXPECTED["source"]["esphome_image"] not in workflow:
        raise RuntimeError("Pinned ESPHome image differs from recovery provenance")

    for key in ("firmware_commit", "ci_commit"):
        commit = EXPECTED["source"][key]
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
            check=True,
            capture_output=True,
        )
    return {
        "schema_version": 1,
        "passed": True,
        "version": EXPECTED["version"],
        "factory_sha256": HAL6_FACTORY_SHA256,
        "source_commits_verified": 2,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        default=root / "docs/hal6-usb-recovery-manifest.json",
    )
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest, root), sort_keys=True))


if __name__ == "__main__":
    main()
