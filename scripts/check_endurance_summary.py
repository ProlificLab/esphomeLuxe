#!/usr/bin/env python3
"""Validate freshness-aware 24-hour endurance evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path


MINIMUM_DURATION_SECONDS = 24 * 60 * 60
MINIMUM_SAMPLE_COUNT = 1400
MAXIMUM_DIAGNOSTIC_AGE_SECONDS = 180
MAXIMUM_HEAP_LOSS = 32768
MAXIMUM_PSRAM_LOSS = 131072
MAXIMUM_EVIDENCE_AGE = timedelta(days=30)
MAXIMUM_FUTURE_SKEW = timedelta(minutes=5)
METRIC_KEYS = {
    "heap_loss",
    "psram_loss",
    "voice_errors_delta",
    "voice_timeouts_delta",
    "voice_no_speech_delta",
    "voice_recoveries_delta",
    "maximum_diagnostic_age_seconds",
    "uptime_regressions",
}
THRESHOLD_KEYS = {
    "max_heap_loss",
    "max_psram_loss",
    "max_new_errors",
    "max_new_timeouts",
    "max_new_no_speech",
    "max_new_recoveries",
    "max_diagnostic_age_seconds",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        fail(f"Endurance {label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Endurance {label} is invalid: {error}")
    if parsed.tzinfo is None:
        fail(f"Endurance {label} must include a timezone")
    return parsed


def validate_summary(path: Path, expected_version: str | None = None) -> dict:
    summary = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "device",
        "started_at",
        "finished_at",
        "observed_duration_seconds",
        "sample_count",
        "metrics",
        "thresholds",
        "failures",
    }
    if not isinstance(summary, dict) or set(summary) != required:
        fail("Endurance summary keys differ from schema")
    if summary["schema_version"] != 2:
        fail("Unsupported endurance summary schema")
    if summary["passed"] is not True or summary["failures"] != []:
        fail("Endurance summary did not pass cleanly")

    started = parse_time(summary["started_at"], "started_at")
    finished = parse_time(summary["finished_at"], "finished_at")
    if finished <= started:
        fail("Endurance timestamps are not increasing")
    now = datetime.now(timezone.utc)
    finished_utc = finished.astimezone(timezone.utc)
    if finished_utc > now + MAXIMUM_FUTURE_SKEW:
        fail("Endurance finished_at is implausibly in the future")
    if finished_utc < now - MAXIMUM_EVIDENCE_AGE:
        fail("Endurance evidence is older than 30 days")
    duration = float(summary["observed_duration_seconds"])
    if not math.isfinite(duration) or duration < MINIMUM_DURATION_SECONDS:
        fail(f"Endurance duration {duration:g}s is shorter than 24 hours")
    wall_duration = (finished - started).total_seconds()
    if wall_duration < MINIMUM_DURATION_SECONDS:
        fail("Endurance wall-clock timestamps span less than 24 hours")
    if abs(wall_duration - duration) > 300:
        fail("Endurance monotonic and wall-clock durations differ by over five minutes")
    if int(summary["sample_count"]) < MINIMUM_SAMPLE_COUNT:
        fail("Endurance evidence has too few samples for a 60-second cadence")

    device = summary["device"]
    if not isinstance(device, dict):
        fail("Endurance device identity is missing")
    for key in ("host", "name", "model", "project_name", "project_version"):
        if not isinstance(device.get(key), str) or not device[key].strip():
            fail(f"Endurance device {key} is missing")
    if expected_version is not None and device["project_version"] != expected_version:
        fail("Endurance firmware version does not match the qualified release")

    metrics = summary["metrics"]
    thresholds = summary["thresholds"]
    if not isinstance(metrics, dict) or set(metrics) != METRIC_KEYS:
        fail("Endurance metrics differ from schema")
    if not isinstance(thresholds, dict) or set(thresholds) != THRESHOLD_KEYS:
        fail("Endurance metrics or thresholds are missing")
    policy_limits = {
        "max_heap_loss": MAXIMUM_HEAP_LOSS,
        "max_psram_loss": MAXIMUM_PSRAM_LOSS,
        "max_new_errors": 0,
        "max_new_timeouts": 0,
        "max_new_no_speech": 3,
        "max_new_recoveries": 0,
        "max_diagnostic_age_seconds": MAXIMUM_DIAGNOSTIC_AGE_SECONDS,
    }
    for name, policy_limit in policy_limits.items():
        value = float(thresholds[name])
        if not math.isfinite(value) or value > policy_limit:
            fail(f"Endurance threshold {name} exceeds release policy")
    diagnostic_age = float(
        metrics.get("maximum_diagnostic_age_seconds", float("inf"))
    )
    if not math.isfinite(diagnostic_age) or diagnostic_age < 0:
        fail("Endurance diagnostic age is invalid")
    if diagnostic_age > min(
        float(thresholds.get("max_diagnostic_age_seconds", 0)),
        MAXIMUM_DIAGNOSTIC_AGE_SECONDS,
    ):
        fail("Endurance diagnostics exceeded the freshness limit")
    for metric, threshold in (
        ("heap_loss", "max_heap_loss"),
        ("psram_loss", "max_psram_loss"),
    ):
        value = float(metrics.get(metric, float("inf")))
        limit = float(thresholds.get(threshold, float("-inf")))
        if not math.isfinite(value) or not math.isfinite(limit) or value > limit:
            fail(f"Endurance {metric} exceeded its recorded threshold")
    for metric in (
        "voice_errors_delta",
        "voice_timeouts_delta",
        "voice_recoveries_delta",
        "uptime_regressions",
    ):
        if float(metrics.get(metric, float("inf"))) != 0:
            fail(f"Endurance {metric} must be zero")
    no_speech = float(metrics.get("voice_no_speech_delta", float("inf")))
    no_speech_limit = min(float(thresholds.get("max_new_no_speech", 0)), 3)
    if (
        not math.isfinite(no_speech)
        or no_speech < 0
        or no_speech > no_speech_limit
    ):
        fail("Endurance no-speech sessions exceeded the closed limit")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    summary = validate_summary(args.summary, args.expected_version)
    print(
        f"Endurance evidence passed: version={summary['device']['project_version']} "
        f"duration={summary['observed_duration_seconds']}s "
        f"samples={summary['sample_count']}."
    )


if __name__ == "__main__":
    main()
