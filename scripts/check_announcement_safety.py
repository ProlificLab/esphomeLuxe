#!/usr/bin/env python3
"""Enforce the bounded queued-announcement and volume-restore contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "media_player.media_stop",
    "media_player.play_media",
    "media_player.volume_set",
    "tts.speak",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing announcement {label}: {marker}")


def require_line(source: str, pattern: str, label: str) -> None:
    if re.search(pattern, source, re.MULTILINE) is None:
        raise RuntimeError(f"Missing exact announcement {label}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_luxe.yaml",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    match = re.search(
        r"^  muse_announce:\n(?P<body>.*?)(?=^  muse_announce_everywhere:)",
        package,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise RuntimeError("Queued announcement script block is missing")
    script = match.group("body")

    require_line(script, r"^\s+mode:\s+queued\s*$", "queue mode")
    require_line(script, r"^\s+max:\s+25\s*$", "queue capacity")
    for marker in (
        'timeout: "00:10:00"',
        "continue_on_timeout: false",
        "input_number.muse_day_volume",
        "input_number.muse_night_volume",
        "input_number.muse_urgent_volume",
        "switch.raspiaudio_muse_luxe_continuous_conversation",
        "['starting', 'listening', 'answering']",
        "previous_volume",
        "volume_level: \"{{ previous_volume | float }}\"",
    ):
        require(script, marker, "policy marker")
    if script.count("continue_on_error: true") < 3:
        raise RuntimeError(
            "Announcement stop, chime and TTS must continue to volume restoration"
        )

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", script, re.MULTILINE))
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Announcement actions are not allowlisted: {sorted(unexpected)}")
    for marker in (
        "notify.",
        "rest_command.",
        "shell_command.",
        "webhook",
    ):
        if marker in script:
            raise RuntimeError(f"Forbidden announcement behavior: {marker}")
    if package.count("media_player.raspiaudio_muse_luxe") < 2:
        raise RuntimeError("Default and whole-home announcement target are missing")
    print("Announcement safety contract passed: bounded queue and volume restore.")


if __name__ == "__main__":
    main()
