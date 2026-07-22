#!/usr/bin/env python3
"""Negative fixtures for the offline rescue safety checker."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_offline_rescue_safety.py"


def rejected(component: str, package: str, preparer: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        paths = {
            "component": directory / "component.cpp",
            "package": directory / "package.yaml",
            "preparer": directory / "prepare.py",
        }
        paths["component"].write_text(component, encoding="utf-8")
        paths["package"].write_text(package, encoding="utf-8")
        paths["preparer"].write_text(preparer, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--component",
                str(paths["component"]),
                "--package",
                str(paths["package"]),
                "--preparer",
                str(paths["preparer"]),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError("Unsafe offline-rescue fixture was accepted")


def main() -> None:
    component = (ROOT / "components/offline_media/offline_media.cpp").read_text()
    package = (ROOT / "packages/offline_rescue.yaml").read_text()
    preparer = (ROOT / "scripts/prepare_rescue_media.py").read_text()
    rejected(component + "\nvoid unsafe() { sdmmc_write_sectors(); }\n", package, preparer)
    rejected(component + '\nconst char *unsafe = "../escape.wav";\n', package, preparer)
    rejected(component, package.replace("max_clip_seconds: 180", "max_clip_seconds: 600"), preparer)
    print("Offline rescue safety negative fixtures passed.")


if __name__ == "__main__":
    main()
