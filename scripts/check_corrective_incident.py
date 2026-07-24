#!/usr/bin/env python3
"""Validate the one closed endurance incident allowed to unlock alpha.6."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re


OLD_VERSION = "2025.3.1-hal.9.0-alpha.5"
MINIMUM_DURATION = 24 * 60 * 60
MINIMUM_SAMPLES = 1400
ERROR_TEXT = "stt-no-text-recognized: No text recognized"
RECORD_KEYS = {
    "schema_version", "passed", "purpose", "old_version", "old_firmware_sha256",
    "raw_sha256", "started_at", "finished_at", "observed_duration_seconds",
    "sample_count", "metrics",
}
METRIC_KEYS = {
    "voice_errors_delta", "voice_recoveries_delta", "voice_timeouts_delta",
    "uptime_regressions", "no_text_samples", "final_voice_state",
    "final_voice_health",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def exact_digest(value: str, label: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        fail(f"{label} must be an exact lowercase SHA-256")


def numeric(sample: dict, key: str, index: int) -> float:
    try:
        value = float(sample[key])
    except (KeyError, TypeError, ValueError) as error:
        fail(f"Incident sample {index} has invalid {key}: {error}")
    if not math.isfinite(value):
        fail(f"Incident sample {index} has non-finite {key}")
    return value


def derive(raw_path: Path, old_artifact: Path, old_sha256: str) -> dict:
    exact_digest(old_sha256, "Old firmware digest")
    if not old_artifact.is_file() or digest(old_artifact) != old_sha256:
        fail("Old firmware artifact does not match its reviewed digest")

    samples = []
    with raw_path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as error:
                fail(f"Incident JSONL line {line_number} is invalid: {error}")
            if not isinstance(sample, dict):
                fail(f"Incident JSONL line {line_number} is not an object")
            samples.append(sample)
    if len(samples) < MINIMUM_SAMPLES:
        fail("Incident evidence has fewer than 1400 samples")

    first, final = samples[0], samples[-1]
    elapsed = numeric(final, "elapsed_seconds", len(samples))
    if elapsed < MINIMUM_DURATION:
        fail("Incident evidence is shorter than 24 hours")
    try:
        started = datetime.fromisoformat(str(first["timestamp"]).replace("Z", "+00:00"))
        finished = datetime.fromisoformat(str(final["timestamp"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as error:
        fail(f"Incident timestamps are invalid: {error}")
    if started.tzinfo is None or finished.tzinfo is None:
        fail("Incident timestamps must include a timezone")
    wall_duration = (finished - started).total_seconds()
    if wall_duration < MINIMUM_DURATION or abs(wall_duration - elapsed) > 300:
        fail("Incident wall-clock and monotonic durations are inconsistent")

    counters = {name: [numeric(sample, name, index) for index, sample in enumerate(samples, 1)]
                for name in ("voice_errors", "voice_recoveries", "voice_timeouts", "uptime")}
    regressions = sum(current < previous for previous, current in zip(counters["uptime"], counters["uptime"][1:]))
    deltas = {name: values[-1] - values[0] for name, values in counters.items() if name != "uptime"}
    if deltas != {"voice_errors": 1.0, "voice_recoveries": 1.0, "voice_timeouts": 0.0}:
        fail("Incident is not the exact +1 error, +1 recovery, zero-timeout profile")
    if regressions != 0:
        fail("Incident uptime regressed")
    for name in ("voice_errors", "voice_recoveries", "voice_timeouts"):
        if any(current < previous for previous, current in zip(counters[name], counters[name][1:])):
            fail(f"Incident counter {name} regressed")

    error_texts = [str(sample.get("last_voice_error", "")) for sample in samples]
    unexpected = {value for value in error_texts if value not in {"", ERROR_TEXT}}
    no_text_samples = sum(value == ERROR_TEXT for value in error_texts)
    if unexpected or no_text_samples == 0:
        fail("Incident contains an unexpected or missing voice error")
    if first.get("voice_state") != "waiting" or first.get("voice_health") != "healthy":
        fail("Incident did not start waiting and healthy")
    final_pair = (str(final.get("voice_state", "")), str(final.get("voice_health", "")))
    if final_pair not in {("waiting", "healthy"), ("offline", "offline")}:
        fail("Incident final voice state is outside the known recovery profile")

    return {
        "schema_version": 1,
        "passed": False,
        "purpose": "corrective-canary-only",
        "old_version": OLD_VERSION,
        "old_firmware_sha256": old_sha256,
        "raw_sha256": digest(raw_path),
        "started_at": first["timestamp"],
        "finished_at": final["timestamp"],
        "observed_duration_seconds": elapsed,
        "sample_count": len(samples),
        "metrics": {
            "voice_errors_delta": 1,
            "voice_recoveries_delta": 1,
            "voice_timeouts_delta": 0,
            "uptime_regressions": 0,
            "no_text_samples": no_text_samples,
            "final_voice_state": final_pair[0],
            "final_voice_health": final_pair[1],
        },
    }


def validate_record(record_path: Path, raw_path: Path, old_artifact: Path,
                    old_sha256: str) -> dict:
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Corrective incident record is invalid: {error}")
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        fail("Corrective incident record keys differ from schema")
    if not isinstance(record.get("metrics"), dict) or set(record["metrics"]) != METRIC_KEYS:
        fail("Corrective incident metrics differ from schema")
    expected = derive(raw_path, old_artifact, old_sha256)
    if record != expected:
        fail("Corrective incident record differs from the raw evidence")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("raw_jsonl", type=Path)
    parser.add_argument("old_artifact", type=Path)
    parser.add_argument("--old-sha256", required=True)
    args = parser.parse_args()
    record = validate_record(args.record, args.raw_jsonl, args.old_artifact, args.old_sha256)
    print(f"Corrective incident passed: samples={record['sample_count']} raw_sha256={record['raw_sha256']}.")


if __name__ == "__main__":
    main()
