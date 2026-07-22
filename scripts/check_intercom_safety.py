#!/usr/bin/env python3
"""Enforce the audible, bounded and transcript-only intercom contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "input_datetime.set_datetime",
    "input_select.select_option",
    "input_text.set_value",
    "logbook.log",
    "script.muse_announce",
    "script.muse_intercom_accept",
    "script.muse_intercom_call",
    "script.muse_intercom_decline",
    "script.muse_intercom_hangup",
    "script.muse_intercom_relay",
    "script.muse_intercom_timeout",
    "timer.cancel",
    "timer.start",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing intercom {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_intercom.yaml",
    )
    parser.add_argument(
        "--sentences",
        type=Path,
        default=root / "home-assistant/custom_sentences/fr/muse_intercom.yaml",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    sentences = args.sentences.read_text(encoding="utf-8")

    for marker in (
        "input_boolean.muse_intercom_enabled",
        "transcript_transient_no_raw_audio_no_duplex",
        "mandatory_chime_on_open_and_relay",
        "duration: \"00:00:45\"",
        "duration: \"00:05:00\"",
        "maximum_session_seconds: 300",
        "bounded_message | length > 240",
        "restart_guard_no_ghost_channel",
        "content intentionally omitted",
        "bureau: media_player.raspiaudio_muse_luxe",
        "cuisine: media_player.muse_luxe_cuisine",
    ):
        require(package, marker, "policy marker")
    for marker in (
        "MuseIntercomCall:",
        "MuseIntercomAccept:",
        "MuseIntercomDecline:",
        "MuseIntercomHangup:",
        "MuseIntercomRelay:",
        "wildcard: true",
    ):
        require(sentences, marker, "local intent")

    if package.count("chime: true") < 5:
        raise RuntimeError("Every opening, relay and terminal notice must be audible")
    room_mappings = set(
        re.findall(
            r"^\s{8}([a-z_]+): (media_player\.[a-z0-9_]+)$",
            package,
            re.MULTILINE,
        )
    )
    expected_mappings = {
        ("bureau", "media_player.raspiaudio_muse_luxe"),
        ("cuisine", "media_player.muse_luxe_cuisine"),
    }
    if room_mappings != expected_mappings:
        raise RuntimeError(f"Intercom room map changed without review: {room_mappings}")
    if re.search(r"selector:\s*\n\s+entity:", package):
        raise RuntimeError("Dynamic entity selectors are forbidden in intercom scripts")
    if re.search(r"value:\s*[\"']?\{\{\s*bounded_message", package):
        raise RuntimeError("Intercom transcript must not be persisted in a helper")

    forbidden = (
        "assist_satellite.announce",
        "assist_satellite.start_conversation",
        "camera.",
        "ffmpeg.",
        "media_player.play_media",
        "microphone.",
        "notify.",
        "shell_command.",
        "voice_assistant.",
        "webhook",
        "http://",
        "https://",
    )
    for marker in forbidden:
        if marker in package:
            raise RuntimeError(f"Forbidden intercom behavior: {marker}")

    action_pattern = re.compile(r"^\s*- action:\s*([^\s#]+)", re.MULTILINE)
    actions = set(action_pattern.findall(package))
    templated = {action for action in actions if "{{" in action or "{%" in action}
    if templated:
        raise RuntimeError(f"Templated intercom actions are forbidden: {templated}")
    unexpected = actions - ALLOWED_ACTIONS
    if unexpected:
        raise RuntimeError(f"Intercom actions are not allowlisted: {sorted(unexpected)}")

    print(
        "Intercom safety contract passed: audible, bounded, transient and "
        "push-to-talk only."
    )


if __name__ == "__main__":
    main()
