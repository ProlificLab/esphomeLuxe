#!/usr/bin/env python3
"""Enforce the opt-in, local and non-critical acoustic guardian contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "input_boolean.turn_off",
    "input_datetime.set_datetime",
    "input_text.set_value",
    "script.muse_announce_everywhere",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing acoustic guardian {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_acoustic_guardian.yaml",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=root / "frigate/acoustic-guardian-policy.example.yaml",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    policy = json.loads(args.policy.read_text(encoding="utf-8"))

    for marker in (
        "initial: fire_alarm",
        "input_boolean.muse_acoustic_guardian_enabled",
        "input_datetime.muse_acoustic_armed_at",
        "topic: frigate/+/audio/+",
        "safe_labels: ['bark', 'crying', 'fire_alarm', 'glass']",
        "restart_privacy_guard",
        "now().timestamp() - armed_at >= 10",
        "cross_check_entity",
        "Vérifiez avec les capteurs dédiés et visuellement",
    ):
        require(package, marker, "policy marker")
    if policy.get("enabled") is not False:
        raise RuntimeError("The repository acoustic policy must default to disabled")
    if policy.get("retention_days") != 1:
        raise RuntimeError("The example acoustic retention must be exactly one day")
    if any(item.get("approved") is not False for item in (policy.get("cameras") or {}).values()):
        raise RuntimeError("Example cameras must not contain consent")

    forbidden = (
        "alarm_control_panel.",
        "button.press",
        "camera.turn_",
        "cover.",
        "lock.",
        "notify.",
        "rest_command.",
        "shell_command.",
        "siren.",
        "switch.turn_",
        "webhook",
    )
    for marker in forbidden:
        if marker in package:
            raise RuntimeError(f"Forbidden acoustic guardian behavior: {marker}")

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", package, re.MULTILINE))
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Acoustic actions are not allowlisted: {sorted(unexpected)}")
    print("Acoustic guardian safety contract passed: local, opt-in and advisory only.")


if __name__ == "__main__":
    main()
