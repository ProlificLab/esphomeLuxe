#!/usr/bin/env python3
"""Validate transactional hal.9 mode qualification evidence."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path


MODE_CASES = (
    ("privacy_on", True, False, "privacy", "privacy"),
    ("privacy_off", False, False, "waiting", "healthy"),
    ("continuous_on", False, True, "listening", "healthy"),
    ("continuous_off", False, False, "waiting", "healthy"),
)
DIAGNOSTICS = {"voice_errors", "voice_timeouts", "voice_recoveries"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        fail(f"Modes evidence {label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Modes evidence {label} is invalid: {error}")
    if parsed.tzinfo is None:
        fail(f"Modes evidence {label} must include a timezone")
    return parsed


def validate_evidence(path: Path, expected_version: str | None = None) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "device",
        "started_at",
        "finished_at",
        "cases",
        "diagnostics_before",
        "diagnostics_after",
        "cleanup",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Modes evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Modes evidence did not pass with schema version 1")

    started = parse_time(evidence["started_at"], "started_at")
    finished = parse_time(evidence["finished_at"], "finished_at")
    if finished <= started:
        fail("Modes evidence timestamps are not increasing")

    device = evidence["device"]
    if not isinstance(device, dict) or set(device) != {
        "host", "name", "model", "project_name", "project_version"
    }:
        fail("Modes evidence device identity is incomplete")
    if any(not isinstance(value, str) or not value.strip() for value in device.values()):
        fail("Modes evidence device identity contains an empty value")
    if expected_version is not None and device["project_version"] != expected_version:
        fail("Modes evidence firmware version does not match")

    cases = evidence["cases"]
    if not isinstance(cases, list) or len(cases) != len(MODE_CASES):
        fail("Modes evidence must contain the four ordered cases")
    previous_time = started
    for actual, expected in zip(cases, MODE_CASES, strict=True):
        if not isinstance(actual, dict) or set(actual) != {
            "name", "observed_at", "privacy_mode", "continuous_conversation",
            "voice_state", "voice_health"
        }:
            fail("Modes evidence case keys differ from schema")
        name, privacy, continuous, voice_state, voice_health = expected
        if (
            actual["name"] != name
            or actual["privacy_mode"] is not privacy
            or actual["continuous_conversation"] is not continuous
            or actual["voice_state"] != voice_state
            or actual["voice_health"] != voice_health
        ):
            fail(f"Modes evidence case {name} has an invalid observed state")
        observed = parse_time(actual["observed_at"], f"case {name}")
        if observed < previous_time or observed > finished:
            fail(f"Modes evidence case {name} timestamp is out of order")
        previous_time = observed

    before = evidence["diagnostics_before"]
    after = evidence["diagnostics_after"]
    if (
        not isinstance(before, dict)
        or not isinstance(after, dict)
        or set(before) != DIAGNOSTICS
        or set(after) != DIAGNOSTICS
    ):
        fail("Modes evidence diagnostic counters differ from schema")
    if before != after:
        fail("Modes evidence diagnostic counters changed")
    for value in before.values():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            fail("Modes evidence diagnostic counter is invalid")

    cleanup = evidence["cleanup"]
    if not isinstance(cleanup, dict) or set(cleanup) != {
        "observed_at",
        "privacy_mode",
        "continuous_conversation",
        "voice_state",
        "voice_health",
    }:
        fail("Modes evidence cleanup keys differ from schema")
    cleanup_time = parse_time(cleanup["observed_at"], "cleanup observed_at")
    if cleanup_time < previous_time or cleanup_time > finished:
        fail("Modes evidence cleanup timestamp is out of order")
    if {key: value for key, value in cleanup.items() if key != "observed_at"} != {
        "privacy_mode": False,
        "continuous_conversation": False,
        "voice_state": "waiting",
        "voice_health": "healthy",
    }:
        fail("Modes evidence does not prove a safe final state")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    evidence = validate_evidence(args.evidence, args.expected_version)
    print(
        "Modes evidence passed: "
        f"version={evidence['device']['project_version']} cases={len(evidence['cases'])}."
    )


if __name__ == "__main__":
    main()
