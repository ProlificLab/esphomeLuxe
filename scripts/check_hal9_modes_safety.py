#!/usr/bin/env python3
"""Enforce fail-closed behavior in the physical hal.9 mode qualification."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Mode qualification is missing {label}: {marker}")


def validate(
    runtime_path: Path,
    validator_path: Path,
    recovery_path: Path,
    voice_path: Path,
) -> None:
    runtime = runtime_path.read_text(encoding="utf-8")
    validator = validator_path.read_text(encoding="utf-8")
    recovery = recovery_path.read_text(encoding="utf-8")
    voice = voice_path.read_text(encoding="utf-8")
    for marker, label in (
        ("--expected-version", "mandatory version argument"),
        ("--output", "mandatory evidence path"),
        ("Evidence already exists", "no-overwrite preflight"),
        ("Firmware version mismatch", "exact firmware binding"),
        ("Active timers present", "active timer refusal"),
        ("Canary must start healthy and waiting", "idle health precondition"),
        ("diagnostics_after != diagnostics_before", "diagnostic delta guard"),
        ("finally:", "unconditional cleanup"),
        (
            'client.switch_command(switches["continuous_conversation"].key, False)',
            "continuous conversation cleanup",
        ),
        (
            'client.switch_command(switches["privacy_mode"].key, False)',
            "privacy cleanup",
        ),
        ("safe cleanup", "verified safe final state"),
        ("cleanup_revisions", "fresh cleanup confirmation"),
        ('latest.get("voice_health") == "busy"', "listening health contract"),
        ("os.replace(temporary_name, path)", "atomic evidence publication"),
    ):
        require(runtime, marker, label)
    if 'parser.add_argument("--expected-version", required=True)' not in runtime:
        raise RuntimeError("Expected firmware version must not have a default")
    if 'parser.add_argument("--output", type=Path, required=True)' not in runtime:
        raise RuntimeError("Evidence output must be mandatory")
    finally_position = runtime.rfind("    finally:")
    publication_position = runtime.rfind("    write_evidence(args.output")
    if finally_position < 0 or publication_position < finally_position:
        raise RuntimeError("Evidence is published before verified cleanup")

    for marker, label in (
        ("MODE_CASES", "closed ordered case set"),
        ("before != after", "unchanged diagnostic counters"),
        ("safe final state", "cleanup validation"),
        ("cleanup timestamp is out of order", "cleanup timestamp validation"),
        ("math.isfinite", "finite diagnostic counters"),
        ("firmware version does not match", "version validation"),
        ("timestamps are not increasing", "bounded evidence timeline"),
        (
            '("continuous_on", False, True, "listening", "busy")',
            "listening evidence contract",
        ),
    ):
        require(validator, marker, label)
    for marker, label in (
        ("case ${P_listening}:", "listening phase"),
        ("case ${P_answering}: return {\"busy\"};", "busy voice health"),
    ):
        require(recovery, marker, label)
    for marker, label in (
        ("id: privacy_mode_switch", "privacy API switch"),
        ("restore_mode: RESTORE_DEFAULT_OFF", "privacy restoration policy"),
        ("script.execute: enter_privacy", "privacy entry action"),
        ("id: continuous_conversation_switch", "continuous API switch"),
        ("lambda: return id(continuous_conversation);", "continuous state source"),
        ("script.execute: start_continuous_conversation", "continuous start action"),
        ("script.execute: stop_continuous_conversation", "continuous stop action"),
    ):
        require(voice, marker, label)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime", type=Path, default=root / "scripts/test_hal9_modes.py"
    )
    parser.add_argument(
        "--validator",
        type=Path,
        default=root / "scripts/check_hal9_modes_evidence.py",
    )
    parser.add_argument(
        "--recovery", type=Path, default=root / "packages/recovery.yaml"
    )
    parser.add_argument(
        "--voice", type=Path, default=root / "packages/voice.yaml"
    )
    args = parser.parse_args()
    validate(args.runtime, args.validator, args.recovery, args.voice)
    print("hal.9 mode qualification safety contract passed.")


if __name__ == "__main__":
    main()
