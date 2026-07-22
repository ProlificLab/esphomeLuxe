#!/usr/bin/env python3
"""Negative fixtures for the queued-announcement safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_announcement_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_luxe.yaml"


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
            raise RuntimeError(f"Unsafe announcement fixture was accepted: {label}")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected(
        package.replace("    max: 25\n", "    max: 100\n", 1),
        "unbounded queue",
    )
    rejected(
        package.replace("    max: 25\n", "    max: 255\n", 1),
        "capacity prefix bypass",
    )
    rejected(
        package.replace('timeout: "00:10:00"', 'timeout: "01:00:00"', 1),
        "long busy wait",
    )
    rejected(
        package.replace("continue_on_timeout: false", "continue_on_timeout: true", 1),
        "play after timeout",
    )
    rejected(
        package.replace("['starting', 'listening', 'answering']", "['starting']", 1),
        "voice-state bypass",
    )
    rejected(
        package.replace("continue_on_error: true", "continue_on_error: false", 1),
        "abort before volume restore",
    )
    rejected(
        package.replace(
            "volume_level: \"{{ previous_volume | float }}\"",
            "volume_level: 1.0",
            1,
        ),
        "lost previous volume",
    )
    rejected(
        package.replace(
            "            - action: tts.speak",
            "            - action: notify.send_message\n            - action: tts.speak",
            1,
        ),
        "external notification",
    )
    print("Announcement safety negative fixtures passed.")


if __name__ == "__main__":
    main()
