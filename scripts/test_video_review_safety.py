#!/usr/bin/env python3
"""Negative fixtures for the authenticated video review checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_video_review_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_video_review.yaml"
DASHBOARD = ROOT / "home-assistant/dashboards/muse-video-review.yaml"
PROVISION = ROOT / "scripts/provision_video_review_dashboard.sh"


def rejected(package: str, dashboard: str, provision: str, label: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        package_path = directory / "package.yaml"
        dashboard_path = directory / "dashboard.yaml"
        provision_path = directory / "provision.sh"
        package_path.write_text(package, encoding="utf-8")
        dashboard_path.write_text(dashboard, encoding="utf-8")
        provision_path.write_text(provision, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--dashboard",
                str(dashboard_path),
                "--provision",
                str(provision_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe video review fixture was accepted: {label}")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    provision = PROVISION.read_text(encoding="utf-8")
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected(
        package + "\n# /api/frigate/notifications/event/snapshot.jpg\n",
        dashboard,
        provision,
        "public notification endpoint",
    )
    rejected(
        package + "\nautomation:\n  - actions:\n      - action: notify.send_message\n",
        dashboard,
        provision,
        "external notification",
    )
    rejected(
        package.replace('duration: "00:05:00"', 'duration: "01:00:00"'),
        dashboard,
        provision,
        "long review window",
    )
    rejected(
        package,
        dashboard.replace("image.sonnette_person", "image.cuisine_person"),
        provision,
        "unreviewed camera",
    )
    rejected(
        package + "\n# face recognition\n",
        dashboard,
        provision,
        "identity processing",
    )
    rejected(
        package,
        dashboard,
        provision.replace("${RESTART_HA:-0}", "${RESTART_HA:-1}"),
        "default restart",
    )
    print("Video review safety negative fixtures passed.")


if __name__ == "__main__":
    main()
