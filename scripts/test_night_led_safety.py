#!/usr/bin/env python3
"""Negative fixtures for the day/night LED profile contract."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_night_led_safety.py"
SOURCES = {
    "package": ROOT / "home-assistant/packages/muse_luxe.yaml",
    "recovery": ROOT / "packages/recovery.yaml",
    "firmware": ROOT / "luxe_microWW.yaml",
    "nabu": ROOT / "luxe_microWW_nabu.yaml",
    "diagnostic": ROOT / "luxe_microWW_diagnostic.yaml",
    "provision": ROOT / "scripts/provision_timer_coach.sh",
}


def rejected(changes: dict[str, tuple[str, str]], label: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        arguments: list[str] = []
        for name, source_path in SOURCES.items():
            source = source_path.read_text(encoding="utf-8")
            if name in changes:
                old, new = changes[name]
                source = source.replace(old, new, 1)
            output = directory / source_path.name
            output.write_text(source, encoding="utf-8")
            arguments.extend((f"--{name}", str(output)))
        result = subprocess.run(
            ["python3", str(CHECKER), *arguments],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe night LED fixture was accepted: {label}")


def main() -> None:
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected({"package": ("'listening': 25", "'listening': 100")}, "bright listening")
    rejected({"package": ("'privacy': 20", "'privacy': 0")}, "invisible privacy")
    rejected(
        {"package": ("entity_id: sensor.raspiaudio_muse_luxe_active_timers", "entity_id: sensor.other")},
        "missing timer trigger",
    )
    rejected(
        {"package": ("brightness_pct: \"{{ desired_brightness | int }}\"", "rgb_color: [0, 0, 0]")},
        "color override",
    )
    rejected(
        {"package": ("entity_id: light.raspiaudio_muse_luxe", "entity_id: light.house")},
        "broad target",
    )
    rejected(
        {
            "recovery": (
                "brightness: !lambda |-\n                  return id(top_led).current_values.get_brightness();",
                "brightness: 40%",
            )
        },
        "timer overwrite",
    )
    rejected(
        {"firmware": ("2025.3.1-hal.9.0-alpha.6", "2025.3.1-hal.9.0-alpha.5")},
        "stale firmware version",
    )
    rejected(
        {"provision": ("${RESTART_HA:-0}", "${RESTART_HA:-1}")},
        "default restart",
    )
    print("Night LED safety negative fixtures passed.")


if __name__ == "__main__":
    main()
