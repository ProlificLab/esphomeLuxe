#!/usr/bin/env python3
"""Negative fixtures for the family message safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_family_message_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_family_messages.yaml"
LEGACY = ROOT / "home-assistant/packages/muse_luxe.yaml"
PROVISION = ROOT / "scripts/provision_family_messages.sh"


def rejected(package: str, legacy: str, provision: str, label: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        package_path = directory / "queue.yaml"
        legacy_path = directory / "legacy.yaml"
        provision_path = directory / "provision.sh"
        package_path.write_text(package, encoding="utf-8")
        legacy_path.write_text(legacy, encoding="utf-8")
        provision_path.write_text(provision, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--legacy-package",
                str(legacy_path),
                "--provision",
                str(provision_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe family message fixture was accepted: {label}")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    legacy = LEGACY.read_text(encoding="utf-8")
    provision = PROVISION.read_text(encoding="utf-8")
    subprocess.run(["python3", str(CHECKER)], check=True)
    rejected(package.replace("capacity: 3", "capacity: 4"), legacy, provision, "fourth slot")
    rejected(
        package.replace(
            "options: [empty, pending, delivering, review]",
            "options: [empty, pending, delivering, review]\n    initial: empty",
            1,
        ),
        legacy,
        provision,
        "restart reset",
    )
    rejected(package.replace("length > 240", "length > 255"), legacy, provision, "long transcript")
    rejected(package.replace(">= 360", ">= 30"), legacy, provision, "premature quarantine")
    rejected(package.replace("state: review", "state: pending", 1), legacy, provision, "no review state")
    rejected(
        package + "\nautomation:\n  - actions:\n      - action: notify.send_message\n",
        legacy,
        provision,
        "external notification",
    )
    rejected(
        package + "\nautomation:\n  - actions:\n      - action: '{{ unsafe_action }}'\n",
        legacy,
        provision,
        "templated action",
    )
    rejected(package, legacy + "\nscript:\n  muse_queue_family_message:\n", provision, "legacy owner")
    rejected(
        package,
        legacy,
        provision.replace("${RESTART_HA:-0}", "${RESTART_HA:-1}"),
        "default restart",
    )
    print("Family message safety negative fixtures passed.")


if __name__ == "__main__":
    main()
