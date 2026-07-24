#!/usr/bin/env python3
"""Enforce the closed, fresh and deduplicated Frigate alert contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "input_datetime.set_datetime",
    "input_text.set_value",
    "script.muse_announce",
}
CAMERAS = {"avant_jardin", "sonnette"}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing video alert {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_video_alerts.yaml",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")

    for marker in (
        "muse_video_alerts_enabled:",
        "initial: 0.75",
        "initial: 60",
        "initial: sonnette,avant_jardin",
        "muse_video_recent_event_ids:",
        "max: 255",
        "event_id | length <= 32 and '|' not in event_id",
        "event_age >= -5 and event_age <= 30",
        "event_id not in recent_event_ids",
        "((recent_event_ids + [event_id])[-7:] | join('|'))[-255:]",
        "stored not in ['unknown', 'unavailable', ''] else []",
        "input_boolean.muse_night_mode",
        "not detection.get('false_positive', false)",
        "label == 'person'",
        "priority: normal",
        "chime: true",
        "- media_player.raspiaudio_muse_luxe",
        "mode: single",
    ):
        require(package, marker, "policy marker")

    match = re.search(
        r"^      closed_cameras:\n(?P<body>(?:        - [a-z0-9_]+\n)+)",
        package,
        re.MULTILINE,
    )
    if match is None:
        raise RuntimeError("Closed video alert camera list is missing")
    cameras = set(re.findall(r"^        - ([a-z0-9_]+)$", match.group("body"), re.MULTILINE))
    if cameras != CAMERAS:
        raise RuntimeError(f"Video alert camera list changed: {sorted(cameras)}")

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", package, re.MULTILINE))
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Video alert actions are not allowlisted: {sorted(unexpected)}")
    if re.search(r"^\s*- action:\s*[\"']?\{\{", package, re.MULTILINE):
        raise RuntimeError("Templated video alert actions are forbidden")
    for marker in (
        "/api/frigate/notifications/",
        "access_token",
        "alarm_control_panel.",
        "camera.",
        "face",
        "http://",
        "https://",
        "notify.",
        "recogn",
        "rest_command.",
        "shell_command.",
        "sub_label",
        "webhook",
    ):
        if marker.lower() in package.lower():
            raise RuntimeError(f"Forbidden video alert behavior: {marker}")
    print("Video alert safety contract passed: fresh, bounded and deduplicated.")


if __name__ == "__main__":
    main()
