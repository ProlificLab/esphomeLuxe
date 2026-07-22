#!/usr/bin/env python3
"""Negative fixtures for the lean diagnostics source contract."""

from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_diagnostics_safety.py"


def rejected(relative_path: str, before: str, after: str) -> None:
    source = ROOT / relative_path
    original = source.read_text(encoding="utf-8")
    if before not in original:
        raise RuntimeError(f"Fixture marker missing from {relative_path}: {before}")
    with tempfile.TemporaryDirectory() as temporary:
        copy = Path(temporary) / "repo"
        required = (
            "packages/diagnostics.yaml",
            "packages/hardware.yaml",
            "components/lean_diagnostics/lean_diagnostics.cpp",
            "luxe_microWW.yaml",
            "luxe_microWW_diagnostic.yaml",
        )
        for item in required:
            destination = copy / item
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / item, destination)
        target = copy / relative_path
        target.write_text(original.replace(before, after, 1), encoding="utf-8")
        result = subprocess.run(
            ["python3", str(CHECKER), "--root", str(copy)],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError(f"Unsafe diagnostics fixture was accepted: {relative_path}")


def main() -> None:
    rejected("luxe_microWW.yaml", "logger_level: ERROR", "logger_level: WARN")
    rejected(
        "luxe_microWW_diagnostic.yaml",
        "logger_level: WARN",
        "logger_level: ERROR",
    )
    rejected(
        "luxe_microWW_diagnostic.yaml",
        "  diagnostics: !include packages/diagnostics.yaml",
        "  diagnostics: !include packages/diagnostics.yaml\n  updates: !include packages/updates.yaml",
    )
    rejected(
        "components/lean_diagnostics/lean_diagnostics.cpp",
        "heap_caps_get_free_size(MALLOC_CAP_SPIRAM)",
        "0",
    )
    rejected("packages/diagnostics.yaml", "lean_diagnostics:", "debug:")
    print("Diagnostics safety negative fixtures passed.")


if __name__ == "__main__":
    main()
