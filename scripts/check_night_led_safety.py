#!/usr/bin/env python3
"""Enforce bounded LED profiles without weakening firmware phase ownership."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing night LED {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_luxe.yaml",
    )
    parser.add_argument(
        "--recovery",
        type=Path,
        default=root / "packages/recovery.yaml",
    )
    parser.add_argument("--firmware", type=Path, default=root / "luxe_microWW.yaml")
    parser.add_argument(
        "--nabu", type=Path, default=root / "luxe_microWW_nabu.yaml"
    )
    parser.add_argument(
        "--diagnostic", type=Path, default=root / "luxe_microWW_diagnostic.yaml"
    )
    parser.add_argument(
        "--provision",
        type=Path,
        default=root / "scripts/provision_timer_coach.sh",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    recovery = args.recovery.read_text(encoding="utf-8")
    firmware = args.firmware.read_text(encoding="utf-8")
    nabu = args.nabu.read_text(encoding="utf-8")
    diagnostic = args.diagnostic.read_text(encoding="utf-8")
    provision = args.provision.read_text(encoding="utf-8")

    profile_marker = "  - id: muse_apply_led_day_night_profile"
    require(package, profile_marker, "automation")
    profile = package[package.index(profile_marker) :]
    for marker in (
        "entity_id: input_boolean.muse_night_mode",
        "entity_id: sensor.raspiaudio_muse_luxe_voice_state",
        "entity_id: sensor.raspiaudio_muse_luxe_active_timers",
        "'starting': 40, 'waiting': 100, 'playing': 60",
        "'listening': 100, 'answering': 100, 'offline': 45",
        "'error': 100, 'privacy': 35, 'rescue': 80",
        "'starting': 15, 'waiting': 10, 'playing': 10",
        "'listening': 25, 'answering': 20, 'offline': 15",
        "'error': 35, 'privacy': 20, 'rescue': 35",
        "15 if is_state('input_boolean.muse_night_mode', 'on') else 40",
        "states('light.raspiaudio_muse_luxe') not in",
        "brightness_pct: \"{{ desired_brightness | int }}\"",
        "continue_on_timeout: false",
        "mode: restart",
    ):
        require(profile, marker, "profile marker")

    forbidden = (
        "brightness: 0",
        "color_name",
        "effect:",
        "hs_color",
        "light.turn_off",
        "rgb_color",
        "xy_color",
    )
    for marker in forbidden:
        if marker in profile:
            raise RuntimeError(f"Night profile may only alter brightness: {marker}")

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", profile, re.MULTILINE))
    if actions != {"light.turn_on"}:
        raise RuntimeError(f"Unexpected night LED actions: {sorted(actions)}")
    lights = set(re.findall(r"light\.[a-z0-9_]+", profile))
    if lights != {"light.raspiaudio_muse_luxe", "light.turn_on"}:
        raise RuntimeError(f"Unexpected night LED targets: {sorted(lights)}")

    timer_block = recovery[
        recovery.index("  - id: refresh_timer_status") :
        recovery.index("  # Recover locally if a voice/TTS exchange")
    ]
    require(
        timer_block,
        "return id(top_led).current_values.get_brightness();",
        "timer brightness preservation",
    )
    if "brightness: 40%" in timer_block:
        raise RuntimeError("Timer ticks still overwrite the selected LED profile")

    for source, version in (
        (firmware, 'version: "2025.3.1-hal.9.0-alpha.5"'),
        (nabu, 'version: "2025.3.1-hal.9.0-alpha.5-nabu"'),
        (diagnostic, 'version: "2025.3.1-hal.9.0-alpha.5-diagnostic"'),
    ):
        require(source, version, "version")

    for marker in (
        "muse_luxe.yaml muse_timer_coach.yaml",
        "guest_exec ha core check",
        "${RESTART_HA:-0}",
    ):
        require(provision, marker, "provisioning guard")
    if "${RESTART_HA:-1}" in provision:
        raise RuntimeError("Night LED provisioning must not restart HA by default")

    print("Night LED safety contract passed: brightness only and timer-safe.")


if __name__ == "__main__":
    main()
