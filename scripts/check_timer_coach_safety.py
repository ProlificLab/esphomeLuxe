#!/usr/bin/env python3
"""Enforce the opt-in, bounded timer checkpoint announcement contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {"script.muse_announce"}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing timer coach {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_timer_coach.yaml",
    )
    parser.add_argument(
        "--base-package",
        type=Path,
        default=root / "home-assistant/packages/muse_luxe.yaml",
    )
    parser.add_argument(
        "--provision",
        type=Path,
        default=root / "scripts/provision_timer_coach.sh",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    base = args.base_package.read_text(encoding="utf-8")
    provision = args.provision.read_text(encoding="utf-8")

    for marker in (
        "muse_timer_checkpoint_announcements",
        "initial: false",
        "sensor.raspiaudio_muse_luxe_nearest_timer_remaining",
        "sensor.raspiaudio_muse_luxe_active_timer_name",
        "sensor.raspiaudio_muse_luxe_active_timers",
        "remaining in [300, 60, 30, 10]",
        "old_remaining > remaining",
        "old_remaining - remaining <= 5",
        "priority: normal",
        "chime: false",
        "mode: queued",
        "max: 4",
    ):
        require(package, marker, "policy marker")

    forbidden = (
        "http://",
        "https://",
        "notify.",
        "persistent_notification.",
        "priority: urgent",
        "rest_command.",
        "shell_command.",
        "webhook",
    )
    for marker in forbidden:
        if marker in package:
            raise RuntimeError(f"Forbidden timer coach behavior: {marker}")

    players = set(re.findall(r"media_player\.[a-z0-9_]+", package))
    if players != {"media_player.raspiaudio_muse_luxe"}:
        raise RuntimeError(f"Timer coach player map changed: {sorted(players)}")

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", package, re.MULTILINE))
    if any("{{" in action or "{%" in action for action in actions):
        raise RuntimeError("Templated timer coach actions are forbidden")
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Timer coach actions are not allowlisted: {sorted(unexpected)}")

    for marker in (
        "muse_voice_state in",
        "['starting', 'listening', 'answering']",
        "switch.raspiaudio_muse_luxe_continuous_conversation",
        "requested_priority == 'urgent'",
        "continue_on_timeout: false",
    ):
        require(base, marker, "conversation queue guard")

    for marker in (
        "pre-timer-coach-${STAMP}",
        "rollback_files",
        "both timer packages were restored",
        "guest_exec ha core check",
        "${RESTART_HA:-0}",
    ):
        require(provision, marker, "provisioning guard")
    if "${RESTART_HA:-1}" in provision:
        raise RuntimeError("Timer coach provisioning must not restart by default")

    print("Timer coach safety contract passed: opt-in checkpoints and no replay.")


if __name__ == "__main__":
    main()
