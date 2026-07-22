#!/usr/bin/env python3
"""Validate candidate-bound physical timer qualification evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


SCENARIOS = {
    "cancel_one_preserves_other",
    "checkpoints_once_day",
    "checkpoints_once_night",
    "conversation_queue_drains_in_order",
    "duration_change_preserved",
    "ha_disconnect_local_completion_audio",
    "ha_disconnect_local_countdown",
    "music_queue_drains_in_order",
    "pause_resume_each_timer",
    "reconnect_no_checkpoint_replay",
    "two_named_timers_visible",
    "urgent_interrupt_preserves_completion",
}
CHECKPOINT_COUNTS = {"300": 1, "60": 1, "30": 1, "10": 1}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Timer {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Timer {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Timer {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Timer observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Timer observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Timer observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Timer evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Timer {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Timer {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_base_package_sha256: str | None = None,
    expected_timer_package_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "metrics",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Timer evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Timer evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "base_package_sha256",
        "timer_package_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Timer candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    base_digest = require_digest(
        candidate["base_package_sha256"], "base_package_sha256"
    )
    timer_digest = require_digest(
        candidate["timer_package_sha256"], "timer_package_sha256"
    )
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (base_digest, expected_base_package_sha256, "base package SHA-256"),
        (timer_digest, expected_timer_package_sha256, "timer package SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Timer {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    metrics = evidence["metrics"]
    metric_keys = {
        "named_timers_created",
        "distinct_timer_names",
        "day_checkpoint_counts",
        "night_checkpoint_counts",
        "replayed_checkpoints_after_reconnect",
        "local_completion_sounds_after_ha_disconnect",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Timer metrics differ from schema")
    if metrics["named_timers_created"] != 2:
        fail("Timer qualification must create exactly two named timers")
    names = metrics["distinct_timer_names"]
    if not isinstance(names, list) or len(names) != 2:
        fail("Timer qualification must record two distinct timer names")
    reviewed_names = [require_text(name, "timer name", minimum=2) for name in names]
    if len(set(reviewed_names)) != 2:
        fail("Timer qualification names are not distinct")
    for period in ("day", "night"):
        if metrics[f"{period}_checkpoint_counts"] != CHECKPOINT_COUNTS:
            fail(f"Timer {period} checkpoints must each occur exactly once")
    if metrics["replayed_checkpoints_after_reconnect"] != 0:
        fail("Timer checkpoints replayed after Home Assistant reconnect")
    if metrics["local_completion_sounds_after_ha_disconnect"] != 1:
        fail("Timer local completion sound was not observed exactly once")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Timer scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-base-package-sha256")
    parser.add_argument("--expected-timer-package-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_base_package_sha256,
        args.expected_timer_package_sha256,
    )
    print(
        "Timer evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
