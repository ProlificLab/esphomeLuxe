#!/usr/bin/env python3
"""Enforce observable no-speech handling without weakening real voice errors."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Voice error classification is missing {label}: {marker}")


def validate(
    voice_path: Path,
    recovery_path: Path,
    diagnostics_path: Path,
    monitor_path: Path,
    summary_path: Path,
) -> None:
    voice = voice_path.read_text(encoding="utf-8")
    recovery = recovery_path.read_text(encoding="utf-8")
    diagnostics = diagnostics_path.read_text(encoding="utf-8")
    monitor = monitor_path.read_text(encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")

    block = voice[voice.index("  on_error:") : voice.index("  on_timer_started:")]
    condition = 'if (code == "stt-no-text-recognized") {'
    if block.count(condition) != 1 or block.count("          return;") != 1:
        raise RuntimeError("No-speech classification must use one exact closed code branch")
    _, classified = block.split(condition, 1)
    no_speech, real_error = classified.split("          return;", 1)
    for marker, label in (
        ("id(voice_no_speech_count)++;", "no-speech counter"),
        ("id(enter_waiting).execute();", "direct healthy return"),
    ):
        require(no_speech, marker, label)
    if "voice_error_count" in no_speech or "recover_voice" in no_speech:
        raise RuntimeError("No-speech branch must not increment or invoke error recovery")
    for marker, label in (
        ("id(voice_error_count)++;", "real error counter"),
        ("id(set_phase).execute(${P_error});", "degraded phase"),
        ("id(handle_voice_error).execute();", "real error recovery"),
    ):
        require(real_error, marker, label)

    for source, marker, label in (
        (recovery, "id: voice_no_speech_count", "no-speech global"),
        (recovery, "id(voice_no_speech_counter).publish_state", "boot publication"),
        (recovery, "id: handle_voice_error", "delayed error handler"),
        (recovery, "delay: 3s", "visible degraded delay"),
        (recovery, "reason: voice_error", "real error recovery reason"),
        (diagnostics, "id: voice_no_speech_counter", "numeric diagnostic"),
        (monitor, '"schema_version": 2', "endurance schema v2"),
        (
            monitor,
            'parser.add_argument("--max-new-no-speech", type=float, default=3)',
            "closed monitor limit",
        ),
        (
            monitor,
            'parser.add_argument("--max-new-recoveries", type=float, default=0)',
            "zero-recovery monitor limit",
        ),
        (summary, '"max_new_no_speech": 3', "closed validator policy"),
        (summary, '"max_new_recoveries": 0', "zero-recovery validator policy"),
        (summary, '"voice_recoveries_delta",', "zero-recovery policy"),
    ):
        require(source, marker, label)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    args = parser.parse_args()
    validate(
        args.root / "packages/voice.yaml",
        args.root / "packages/recovery.yaml",
        args.root / "packages/diagnostics.yaml",
        args.root / "scripts/monitor_endurance.py",
        args.root / "scripts/check_endurance_summary.py",
    )
    print("Voice no-speech classification is closed, observable and bounded.")


if __name__ == "__main__":
    main()
