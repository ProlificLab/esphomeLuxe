#!/usr/bin/env python3
"""Enforce lean production diagnostics and an isolated verbose image."""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing diagnostics {label}: {marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    root = parser.parse_args().root
    package = (root / "packages/diagnostics.yaml").read_text(encoding="utf-8")
    hardware = (root / "packages/hardware.yaml").read_text(encoding="utf-8")
    component = (root / "components/lean_diagnostics/lean_diagnostics.cpp").read_text(
        encoding="utf-8"
    )
    firmware = (root / "luxe_microWW.yaml").read_text(encoding="utf-8")
    diagnostic = (root / "luxe_microWW_diagnostic.yaml").read_text(
        encoding="utf-8"
    )

    for marker in (
        "heap_free:",
        "heap_max_block:",
        "loop_time:",
        "free_psram:",
        "reset_reason:",
        "level: ${logger_level}",
    ):
        require(package, marker, "entity or logger contract")
    for marker in (
        "heap_caps_get_free_size(MALLOC_CAP_INTERNAL)",
        "heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)",
        "heap_caps_get_free_size(MALLOC_CAP_SPIRAM)",
        "esp_reset_reason()",
    ):
        require(component, marker, "ESP32 measurement")
    require(hardware, "lean_diagnostics", "local component pin")
    require(firmware, "logger_level: ERROR", "production compile level")
    require(
        firmware,
        'version: "2025.3.1-hal.9.0-alpha.5"',
        "production version",
    )
    require(diagnostic, "logger_level: WARN", "verbose compile level")
    require(
        diagnostic,
        'version: "2025.3.1-hal.9.0-alpha.5-diagnostic"',
        "diagnostic identity",
    )
    if "updates: !include" in diagnostic or "platform: http_request" in diagnostic:
        raise RuntimeError("Verbose diagnostic image must not self-update")
    if "debug:" in package or "platform: debug" in package:
        raise RuntimeError("Generic debug component returned to the production graph")
    if "CPU Frequency" in package:
        raise RuntimeError("Static CPU frequency must not consume a runtime entity")

    print("Diagnostics safety contract passed: lean production and isolated WARN image.")


if __name__ == "__main__":
    main()
