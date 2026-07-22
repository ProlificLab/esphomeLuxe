#!/usr/bin/env python3
"""Enforce bounded, explicit and crash-aware Music Assistant operations."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "input_datetime.set_datetime",
    "input_select.select_option",
    "input_text.set_value",
    "media_player.join",
    "media_player.unjoin",
    "media_player.volume_set",
    "music_assistant.play_announcement",
    "music_assistant.transfer_queue",
    "script.muse_clear_temporary_audio_group_state",
    "script.muse_close_temporary_audio_group",
    "timer.cancel",
    "timer.start",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing Music Assistant {label}: {marker}")


def ordered(source: str, first: str, second: str, label: str) -> None:
    first_index = source.find(first)
    second_index = source.find(second)
    if first_index < 0 or second_index < 0 or first_index >= second_index:
        raise RuntimeError(f"Invalid Music Assistant ordering for {label}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_music_assistant.yaml",
    )
    parser.add_argument(
        "--provision",
        type=Path,
        default=root / "scripts/provision_music_assistant.sh",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    provision = args.provision.read_text(encoding="utf-8")

    for marker in (
        "muse_audio_follow_enabled",
        "options: [idle, grouping, active, closing, review]",
        "restore: true",
        "candidate_players | length < 2",
        "candidate_players | length > 4",
        "group_minutes < 5 or group_minutes > 240",
        "player.startswith('media_player.raspiaudio_muse_luxe')",
        "states(player) in ['unknown', 'unavailable']",
        "requested_players | length != candidate_players | length",
        "volume_snapshot",
        "repeat.item.volume",
        "continue_on_timeout: false",
        "confirm_cleanup",
        "not confirmed or not valid_players",
        "['grouping', 'closing', 'review']",
        "now().timestamp() - claimed >= 120",
        "seconds: \"30\"",
        "trigger.id in ['startup', 'watchdog']",
        "event_type: timer.finished",
        "entity_id: timer.muse_audio_temporary_group",
        "Restart recovery never issues an automatic unjoin command.",
        "blocked_group_active",
    ):
        require(package, marker, "policy marker")

    if package.count("initial:") != 1 or "initial: idle" not in package:
        raise RuntimeError("Only transfer status may have an initial value")
    if package.count("action: media_player.join") != 1:
        raise RuntimeError("Exactly one guarded group creation action is allowed")
    if package.count("action: media_player.unjoin") != 2:
        raise RuntimeError("Ungrouping must exist only in close and explicit recovery")
    if package.count("states(player) in ['unknown', 'unavailable']") != 3:
        raise RuntimeError("Every group lifecycle path must reject unavailable players")

    forbidden = (
        "notify.",
        "persistent_notification.",
        "rest_command.",
        "shell_command.",
        "webhook",
        "person.",
        "zone.",
        "state: \"on\"\n    icon: mdi:account-music-outline",
    )
    for marker in forbidden:
        if marker in package:
            raise RuntimeError(f"Forbidden Music Assistant behavior: {marker}")

    urls = set(re.findall(r"https?://[^\s'\")]+", package))
    allowed_url = "http://10.10.30.159:8123/local/muse-luxe/"
    if urls != {allowed_url}:
        raise RuntimeError(f"Music Assistant URL policy changed: {sorted(urls)}")

    media_player_tokens = set(re.findall(r"media_player\.[a-z0-9_]+", package))
    allowed_tokens = {
        "media_player.join",
        "media_player.raspiaudio_muse_luxe",
        "media_player.raspiaudio_muse_luxe_2",
        "media_player.unjoin",
        "media_player.volume_set",
    }
    if unexpected_tokens := media_player_tokens - allowed_tokens:
        raise RuntimeError(
            f"Unexpected fixed Music Assistant players: {sorted(unexpected_tokens)}"
        )

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", package, re.MULTILINE))
    if any("{{" in action or "{%" in action for action in actions):
        raise RuntimeError("Templated Music Assistant actions are forbidden")
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Music Assistant actions are not allowlisted: {sorted(unexpected)}")

    ordered(package, "option: grouping", "action: media_player.join", "claim before join")
    ordered(package, "option: closing", "action: media_player.unjoin", "claim before unjoin")
    ordered(
        package,
        "action: media_player.unjoin",
        "action: script.muse_clear_temporary_audio_group_state",
        "clear after unjoin",
    )

    for marker in (
        "pre-audio-groups-${STAMP}",
        "rollback_file",
        "guest_exec ha core check",
        "Music Assistant package was restored",
        "${RESTART_HA:-0}",
    ):
        require(provision, marker, "provisioning guard")
    if "${RESTART_HA:-1}" in provision:
        raise RuntimeError("Music Assistant provisioning must not restart by default")

    print("Music Assistant safety contract passed: bounded manual groups and review.")


if __name__ == "__main__":
    main()
