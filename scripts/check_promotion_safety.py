#!/usr/bin/env python3
"""Keep beta/stable publication atomic and qualification-gated."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(source: str, marker: str, label: str) -> int:
    position = source.find(marker)
    if position < 0:
        raise RuntimeError(f"Missing promotion {label}: {marker}")
    return position


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--promotion",
        type=Path,
        default=root / "scripts/promote_firmware_channel.sh",
    )
    parser.add_argument(
        "--packager",
        type=Path,
        default=root / "scripts/package_firmware.sh",
    )
    args = parser.parse_args()
    promotion = args.promotion.read_text(encoding="utf-8")
    packager = args.packager.read_text(encoding="utf-8")

    clean = require(promotion, "Promotion requires a clean Git worktree", "clean-tree guard")
    clean_build = require(promotion, 'clean "$config"', "clean firmware build")
    compile_build = require(promotion, 'compile "$config"', "firmware compilation")
    versioned = require(
        promotion,
        '"muse-luxe/channels/$CHANNEL/firmware-$version.ota.bin"',
        "immutable artifact path",
    )
    verified = require(
        promotion,
        '"$SCRIPT_DIR/verify_release.sh" "$manifest" "$artifact"',
        "artifact verification",
    )
    qualified = require(
        promotion,
        'python3 "$SCRIPT_DIR/check_qualification_record.py"',
        "qualification verification",
    )
    activation_comment = require(
        promotion,
        "# The manifest is the activation point and must remain the final publication.",
        "activation policy",
    )
    manifest_destination = require(
        promotion,
        '"$manifest" "muse-luxe/channels/$CHANNEL/manifest.json"',
        "manifest publication",
    )
    if not clean < clean_build < compile_build < verified < qualified < versioned < activation_comment < manifest_destination:
        raise RuntimeError("Promotion verification/publication order is unsafe")
    if "publish_ha_file.sh" in promotion[manifest_destination + 1 :]:
        raise RuntimeError("A publication occurs after the activation manifest")
    if 'channels/$CHANNEL/firmware.ota.bin' in promotion:
        raise RuntimeError("Mutable beta/stable firmware path is forbidden")
    require(packager, '"source_commit": "$(git rev-parse HEAD)"', "source attestation")
    require(
        packager,
        'firmware-$version.ota.bin',
        "versioned beta/stable manifest path",
    )

    print(
        "Promotion safety contract passed: clean, qualified, versioned and "
        "manifest-last."
    )


if __name__ == "__main__":
    main()
