#!/usr/bin/env python3
"""Negative fixtures for the intercom safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_intercom_safety.py"


def rejected(package: str, sentences: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        package_path = directory / "package.yaml"
        sentences_path = directory / "sentences.yaml"
        package_path.write_text(package, encoding="utf-8")
        sentences_path.write_text(sentences, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--sentences",
                str(sentences_path),
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
    rejected(package.replace("chime: true", "chime: false"), sentences)
    rejected(
        package + "\nscript:\n  unsafe:\n    sequence:\n      - action: voice_assistant.start\n",
        sentences,
    )
    rejected(
        package.replace(
            'value: "relay:{{ requested_source }}:{{ destination_room }}"',
            'value: "{{ bounded_message }}"',
        ),
        sentences,
    )
    rejected(package.replace("maximum_session_seconds: 300", "maximum_session_seconds: 900"), sentences)
    rejected(package, sentences.replace("wildcard: true", "wildcard: false"))
    rejected(
        package.replace(
            "cuisine: media_player.muse_luxe_cuisine",
            "cuisine: \"{{ target_player }}\"",
        ),
        sentences,
    )
    print("Intercom safety negative fixtures passed.")


if __name__ == "__main__":
    main()
