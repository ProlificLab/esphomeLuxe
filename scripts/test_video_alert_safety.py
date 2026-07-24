#!/usr/bin/env python3
"""Negative fixtures for the Frigate alert safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_video_alert_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_video_alerts.yaml"


def rejected(package: str, label: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "package.yaml"
        path.write_text(package, encoding="utf-8")
        result = subprocess.run(
            ["python3", str(CHECKER), "--package", str(path)],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe video alert fixture was accepted: {label}")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected(
        package.replace("event_age <= 30", "event_age <= 3600"),
        "stale event",
    )
    rejected(
        package.replace("[-7:] | join('|')", "[-1:] | join('|')"),
        "one-event history",
    )
    rejected(
        package.replace("event_id not in recent_event_ids", "event_id != recent_event_ids[-1]"),
        "last-event-only deduplication",
    )
    rejected(
        package.replace("        - avant_jardin\n", "        - cuisine\n", 1),
        "unreviewed camera",
    )
    rejected(
        package.replace("input_boolean.muse_night_mode", "input_boolean.always_off"),
        "night bypass",
    )
    rejected(
        package.replace("mode: single", "mode: parallel"),
        "concurrent claims",
    )
    rejected(
        package + "\nautomation:\n  - actions:\n      - action: notify.send_message\n",
        "external notification",
    )
    rejected(
        package.replace(
            "- media_player.raspiaudio_muse_luxe",
            "- media_player.unreviewed",
        ),
        "unreviewed target",
    )
    print("Video alert safety negative fixtures passed.")


if __name__ == "__main__":
    main()
