#!/usr/bin/env python3
"""Negative fixtures for the intercom safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_intercom_safety.py"


def rejected(package: str, sentences: str, ui: str, recovery: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        package_path = directory / "package.yaml"
        sentences_path = directory / "sentences.yaml"
        ui_path = directory / "ui.yaml"
        recovery_path = directory / "recovery.yaml"
        package_path.write_text(package, encoding="utf-8")
        sentences_path.write_text(sentences, encoding="utf-8")
        ui_path.write_text(ui, encoding="utf-8")
        recovery_path.write_text(recovery, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--sentences",
                str(sentences_path),
                "--ui",
                str(ui_path),
                "--recovery",
                str(recovery_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError("Unsafe intercom fixture was accepted")


def main() -> None:
    package = (ROOT / "home-assistant/packages/muse_intercom.yaml").read_text()
    sentences = (
        ROOT / "home-assistant/custom_sentences/fr/muse_intercom.yaml"
    ).read_text()
    ui = (ROOT / "packages/ui.yaml").read_text()
    recovery = (ROOT / "packages/recovery.yaml").read_text()
    rejected(package.replace("chime: true", "chime: false"), sentences, ui, recovery)
    rejected(
        package + "\nscript:\n  unsafe:\n    sequence:\n      - action: voice_assistant.start\n",
        sentences,
        ui,
        recovery,
    )
    rejected(
        package.replace(
            'value: "relay:{{ requested_source }}:{{ destination_room }}"',
            'value: "{{ bounded_message }}"',
        ),
        sentences,
        ui,
        recovery,
    )
    rejected(package.replace("maximum_session_seconds: 300", "maximum_session_seconds: 900"), sentences, ui, recovery)
    rejected(package, sentences.replace("wildcard: true", "wildcard: false"), ui, recovery)
    rejected(
        package.replace(
            "cuisine: media_player.muse_luxe_cuisine",
            "cuisine: \"{{ target_player }}\"",
        ),
        sentences,
        ui,
        recovery,
    )
    rejected(
        package.replace("requested_session != active_session", "false", 1),
        sentences,
        ui,
        recovery,
    )
    rejected(
        package.replace(
            'required_intercom_status: connected',
            'required_intercom_status: ringing',
            1,
        ),
        sentences,
        ui,
        recovery,
    )
    rejected(
        package.replace(
            "rejectattr('state', 'in', ['unknown', 'unavailable'])",
            "selectattr('state', 'defined')",
            1,
        ),
        sentences,
        ui,
        recovery,
    )
    rejected(
        package,
        sentences.replace("MuseIntercomCallFrom:", "UnsafeCallFrom:"),
        ui,
        recovery,
    )
    rejected(
        package,
        sentences,
        ui.replace(
            'case 2: return std::string("double_click")',
            'case 2: return std::string("single_click")',
            1,
        ),
        recovery,
    )
    rejected(
        package,
        sentences,
        ui,
        recovery.replace("id: manual_listen", "id: unsafe_manual_listen", 1),
    )
    print("Intercom safety negative fixtures passed.")


if __name__ == "__main__":
    main()
