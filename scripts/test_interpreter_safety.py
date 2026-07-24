#!/usr/bin/env python3
"""Exercise negative fixtures for the interpreter safety policy."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_interpreter_safety.py"
PACKAGE = ROOT / "home-assistant/packages/muse_interpreter.yaml"
CONFIG = ROOT / "scripts/configure_interpreter.py"


def rejected(package: str, config: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        package_path = root / "package.yaml"
        config_path = root / "configure.py"
        package_path.write_text(package, encoding="utf-8")
        config_path.write_text(config, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--package",
                str(package_path),
                "--config",
                str(config_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError("Unsafe interpreter fixture was accepted")


def main() -> None:
    package = PACKAGE.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    rejected(package + "\n      - action: lock.unlock\n", config)
    rejected(package.replace('duration: "00:10:00"', 'duration: "01:00:00"'), config)
    rejected(package, config + '\nunsafe = {"llm_hass_api": ["assist"]}\n')
    print("Interpreter safety negative fixtures passed.")


if __name__ == "__main__":
    main()
