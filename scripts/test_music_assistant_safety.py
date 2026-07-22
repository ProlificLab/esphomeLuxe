#!/usr/bin/env python3
"""Positive and negative fixtures for Music Assistant safety policy."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_music_assistant_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_music_assistant.yaml"
PROVISION = ROOT / "scripts/provision_music_assistant.sh"


def rejected(package: str, provision: str, label: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        package_path = directory / "music.yaml"
        provision_path = directory / "provision.sh"
        package_path.write_text(package, encoding="utf-8")
        provision_path.write_text(provision, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--provision",
                str(provision_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe Music Assistant fixture was accepted: {label}")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    provision = PROVISION.read_text(encoding="utf-8")
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected(
        package.replace(
            "icon: mdi:account-music-outline",
            "icon: mdi:account-music-outline\n    initial: true",
        ),
        provision,
        "default on",
    )
    rejected(package.replace("candidate_players | length > 4", "candidate_players | length > 8"), provision, "eight players")
    rejected(package.replace("group_minutes > 240", "group_minutes > 1440"), provision, "day-long group")
    rejected(package.replace("media_player.raspiaudio_muse_luxe", "media_player."), provision, "broad player prefix")
    rejected(package.replace("not confirmed or not valid_players", "not valid_players"), provision, "missing confirmation")
    rejected(package.replace("continue_on_timeout: false", "continue_on_timeout: true", 1), provision, "join timeout ignored")
    rejected(package.replace("states(player) in ['unknown', 'unavailable']", "false", 1), provision, "unavailable player")
    rejected(package.replace('seconds: "30"', 'seconds: "0"'), provision, "expiry race")
    rejected(package.replace("event_type: timer.finished", "event_type: timer.started"), provision, "wrong expiry event")
    rejected(package + "\nautomation:\n  - trigger: state\n    entity_id: person.anna\n", provision, "presence automation")
    rejected(package + "\naction:\n  - action: notify.send_message\n", provision, "external notification")
    rejected(package + "\naction:\n  - action: media_player.unjoin\n", provision, "extra automatic unjoin")
    rejected(
        package,
        provision.replace("${RESTART_HA:-0}", "${RESTART_HA:-1}"),
        "default restart",
    )
    print("Music Assistant safety negative fixtures passed.")


if __name__ == "__main__":
    main()
