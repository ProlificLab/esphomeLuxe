#!/usr/bin/env python3
"""Enforce the bounded and crash-aware family message queue contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "input_boolean.turn_off",
    "input_datetime.set_datetime",
    "input_select.select_option",
    "input_text.set_value",
    "persistent_notification.create",
    "persistent_notification.dismiss",
    "script.muse_clear_family_message_slot",
    "script.muse_clear_legacy_pending_message",
    "script.muse_discard_family_message_slot",
    "script.muse_intercom_message",
    "script.muse_process_family_message_slot",
    "script.muse_queue_family_message",
    "script.muse_set_message_slot_state",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing family message {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_family_messages.yaml",
    )
    parser.add_argument(
        "--legacy-package",
        type=Path,
        default=root / "home-assistant/packages/muse_luxe.yaml",
    )
    parser.add_argument(
        "--provision",
        type=Path,
        default=root / "scripts/provision_family_messages.sh",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    legacy = args.legacy_package.read_text(encoding="utf-8")
    provision = args.provision.read_text(encoding="utf-8")

    for slot in (1, 2, 3):
        for suffix in ("state", "id", "text", "recipient", "target", "expiry", "claimed_at"):
            require(package, f"muse_message_slot_{slot}_{suffix}", f"slot {slot} field")
    for marker in (
        "options: [empty, pending, delivering, review]",
        "capacity: 3",
        "automatic_delivery: at_most_once_with_uncertain_quarantine",
        "bounded_message | length > 240",
        "expiry_minutes < 5 or expiry_minutes > 1440",
        "free_slot | int(0) not in [1, 2, 3]",
        "state: delivering",
        "state: review",
        "trigger.id == 'startup'",
        "now().timestamp() - claimed_at >= 360",
        "legacy_expiry <= now().timestamp()",
        "ns.items | sort",
        "choisissez explicitement retry ou discard",
        "muse_family_message_legacy_migration",
        "script.muse_clear_legacy_pending_message",
    ):
        require(package.lower(), marker.lower(), "policy marker")

    if package.count("name: Muse family message slot ") < 21:
        raise RuntimeError("The three message slots are incomplete")
    if "initial:" in package:
        raise RuntimeError("Message queue helpers must restore state after HA restart")
    if "muse_queue_family_message:" in legacy:
        raise RuntimeError("The legacy package still owns the queue script")
    if "muse_pending_message_dispatch" in legacy:
        raise RuntimeError("The legacy one-slot dispatcher is still active")

    forbidden = (
        "camera.",
        "http://",
        "https://",
        "input_boolean.turn_on",
        "notify.",
        "rest_command.",
        "shell_command.",
        "voice_assistant.",
        "webhook",
    )
    for marker in forbidden:
        if marker in package:
            raise RuntimeError(f"Forbidden family message behavior: {marker}")

    players = set(re.findall(r"media_player\.[a-z0-9_]+", package))
    if players != {"media_player.raspiaudio_muse_luxe"}:
        raise RuntimeError(f"Family message player map changed: {sorted(players)}")

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", package, re.MULTILINE))
    if any("{{" in action or "{%" in action for action in actions):
        raise RuntimeError("Templated family message actions are forbidden")
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Family message actions are not allowlisted: {sorted(unexpected)}")

    templated_targets = re.findall(r'^\s+entity_id:\s*"([^\n]*\{\{[^\n]+)"$', package, re.MULTILINE)
    for target in templated_targets:
        if not target.startswith(("input_text.muse_message_slot_", "input_datetime.muse_message_slot_", "input_select.muse_message_slot_")):
            raise RuntimeError(f"Unsafe templated family message target: {target}")
    for marker in (
        "pre-family-messages-${STAMP}",
        "rollback_files",
        "both message packages were restored",
        "guest_exec ha core check",
        '${RESTART_HA:-0}',
    ):
        require(provision, marker, "provisioning guard")
    if "${RESTART_HA:-1}" in provision:
        raise RuntimeError("Family-message provisioning must not restart by default")
    print("Family message safety contract passed: three slots and no automatic replay.")


if __name__ == "__main__":
    main()
