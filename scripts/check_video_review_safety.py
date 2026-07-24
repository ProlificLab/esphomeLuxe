#!/usr/bin/env python3
"""Enforce the closed, authenticated and short-lived video review contract."""

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
    "timer.cancel",
    "timer.start",
}
ALLOWED_IMAGES = {"image.avant_jardin_person", "image.sonnette_person"}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing video review {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_video_review.yaml",
    )
    parser.add_argument(
        "--dashboard",
        type=Path,
        default=root / "home-assistant/dashboards/muse-video-review.yaml",
    )
    parser.add_argument(
        "--provision",
        type=Path,
        default=root / "scripts/provision_video_review_dashboard.sh",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    dashboard = args.dashboard.read_text(encoding="utf-8")
    provision = args.provision.read_text(encoding="utf-8")

    for marker in (
        "initial: disabled",
        "initial: none",
        "restart_privacy_guard",
        'duration: "00:05:00"',
        "now().timestamp() - armed_at >= 10",
        "now().timestamp() - image_updated <= 30",
        "closed_camera_map:",
        "sonnette: image.sonnette_person",
        "avant_jardin: image.avant_jardin_person",
        "Vérifiez qu'elle correspond",
    ):
        require(package, marker, "policy marker")

    forbidden = (
        "/api/frigate/notifications/",
        "access_token",
        "camera.turn_",
        "face",
        "http://",
        "https://",
        "media_player.play_media",
        "notify.",
        "recogn",
        "rest_command.",
        "shell_command.",
        "sub_label",
        "webhook",
    )
    combined = package + "\n" + dashboard
    for marker in forbidden:
        if marker.lower() in combined.lower():
            raise RuntimeError(f"Forbidden video review behavior: {marker}")

    actions = set(re.findall(r"^\s*- action:\s*([^\s#]+)", package, re.MULTILINE))
    if unexpected := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Video review actions are not allowlisted: {sorted(unexpected)}")
    dashboard_images = set(re.findall(r"entity:\s*(image\.[a-z0-9_]+)", dashboard))
    if dashboard_images != ALLOWED_IMAGES:
        raise RuntimeError(f"Video review image map changed: {sorted(dashboard_images)}")
    package_images = set(re.findall(r"image\.[a-z0-9_]+", package))
    if package_images != ALLOWED_IMAGES:
        raise RuntimeError(f"Package image map changed: {sorted(package_images)}")
    for marker in (
        "HA_DESTINATION_ROOT=/config/packages",
        "HA_DESTINATION_ROOT=/config/dashboards",
        "pre-muse-video-review-${STAMP}",
        "rollback_files",
        "all changed files were restored",
        "An existing lovelace block needs a manual dashboard merge; refusing.",
        "guest_exec ha core check",
        '${RESTART_HA:-0}',
    ):
        require(provision, marker, "provisioning guard")
    if "${RESTART_HA:-1}" in provision:
        raise RuntimeError("Video review provisioning must not restart HA by default")
    print("Video review safety contract passed: authenticated, closed and ephemeral.")


if __name__ == "__main__":
    main()
