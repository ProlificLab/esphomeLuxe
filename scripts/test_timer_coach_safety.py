#!/usr/bin/env python3
"""Negative fixtures for the timer coach safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_timer_coach_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_timer_coach.yaml"
BASE = ROOT / "home-assistant/packages/muse_luxe.yaml"
PROVISION = ROOT / "scripts/provision_timer_coach.sh"


def rejected(package: str, base: str, provision: str, label: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        package_path = directory / "timer.yaml"
        base_path = directory / "base.yaml"
        provision_path = directory / "provision.sh"
        package_path.write_text(package, encoding="utf-8")
        base_path.write_text(base, encoding="utf-8")
        provision_path.write_text(provision, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--base-package",
                str(base_path),
                "--provision",
                str(provision_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe timer coach fixture was accepted: {label}")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    base = BASE.read_text(encoding="utf-8")
    provision = PROVISION.read_text(encoding="utf-8")
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected(package.replace("initial: false", "initial: true"), base, provision, "default on")
    rejected(package.replace("[300, 60, 30, 10]", "[600, 300, 60, 30, 10]"), base, provision, "extra checkpoint")
    rejected(package.replace("<= 5", "<= 300"), base, provision, "reconnect replay")
    rejected(package.replace("priority: normal", "priority: urgent"), base, provision, "urgent checkpoint")
    rejected(package + "\naction:\n  - action: notify.send_message\n", base, provision, "external notification")
    rejected(
        package,
        base.replace("['starting', 'listening', 'answering']", "['starting']"),
        provision,
        "conversation bypass",
    )
    rejected(
        package,
        base,
        provision.replace("${RESTART_HA:-0}", "${RESTART_HA:-1}"),
        "default restart",
    )
    print("Timer coach safety negative fixtures passed.")


if __name__ == "__main__":
    main()
