#!/usr/bin/env python3
"""Enforce the fixed-file, no-format safety contract for offline rescue audio."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


FIXED_FILES = {
    "READY.WAV",
    "POWER.WAV",
    "PWRLIST.WAV",
    "EVAC.WAV",
    "EVACLIST.WAV",
    "ALLCLEAR.WAV",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing offline-rescue {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", type=Path, default=root / "components/offline_media/offline_media.cpp")
    parser.add_argument("--package", type=Path, default=root / "packages/offline_rescue.yaml")
    parser.add_argument("--preparer", type=Path, default=root / "scripts/prepare_rescue_media.py")
    args = parser.parse_args()
    component = args.component.read_text(encoding="utf-8")
    package = args.package.read_text(encoding="utf-8")
    preparer = args.preparer.read_text(encoding="utf-8")
    firmware = (root / "luxe_microWW.yaml").read_text(encoding="utf-8")
    calibration_firmware = (root / "luxe_microWW_nabu.yaml").read_text(encoding="utf-8")
    ui = (root / "packages/ui.yaml").read_text(encoding="utf-8")

    for marker in (
        "cs_pin: 13",
        "clk_pin: 14",
        "mosi_pin: 15",
        "miso_pin: 2",
        "max_clip_seconds: 180",
        "id: toggle_rescue_mode",
        "id: play_next_rescue_clip",
        "Privacy mode blocks rescue audio entry",
        "internal: true",
    ):
        require(package, marker, "package guard")
    require(ui, "gesture: quadruple_click", "physical entry/exit")
    require(ui, "clip: evacuation", "physical evacuation shortcut")
    require(component, "command_(17, address", "raw read-only sector access")
    require(component, "fixed 8.3 names, no write operations", "read-only policy")
    require(component, "data_size <= maximum_bytes", "duration bound")
    require(package, "speaker.is_stopped", "media-player preemption wait")
    require(package, "return !id(rescue_media).is_playing();", "local preemption wait")
    require(
        (root / "packages/recovery.yaml").read_text(encoding="utf-8"),
        "id(rescue_media).stop();",
        "privacy stop",
    )
    require(firmware, 'version: "2025.3.1-hal.9.0-alpha.4"', "firmware version")
    for marker in (
        'P_rescue: "8"',
        "offline_rescue: !include packages/offline_rescue.yaml",
        'version: "2025.3.1-hal.9.0-alpha.4-nabu"',
    ):
        require(calibration_firmware, marker, "calibration parity")

    component_names = set(re.findall(r'return "([A-Z ]{8}WAV)";', component))
    component_files = {
        f"{name[:8].rstrip()}.{name[8:]}" for name in component_names
    }
    preparer_files = set(re.findall(r'^\s+"([A-Z]+\.WAV)",$', preparer, re.MULTILINE))
    if component_files != FIXED_FILES or preparer_files != FIXED_FILES:
        raise RuntimeError(
            f"Firmware/preparer fixed-file mismatch: {component_files=} {preparer_files=}"
        )
    forbidden = (
        "sdmmc_write_sectors",
        "command_(24,",
        "esp_vfs_fat",
        "fopen(",
        "../",
        "http://",
        "https://",
    )
    for marker in forbidden:
        if marker in component:
            raise RuntimeError(f"Forbidden offline-rescue component behavior: {marker}")
    if re.search(r"^button:\s*$", package, re.MULTILINE):
        raise RuntimeError("Home Assistant rescue playback buttons are forbidden")
    if "MAX_SECONDS = 180" not in preparer or "CARD_LABEL = \"MUSE_RESCUE\"" not in preparer:
        raise RuntimeError("Card preparer lacks duration or destination guards")

    print("Offline rescue safety contract passed: fixed, bounded, local and no-format.")


if __name__ == "__main__":
    main()
