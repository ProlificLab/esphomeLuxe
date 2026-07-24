#!/usr/bin/env python3
"""Validate candidate-bound physical routed-announcement evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


TARGETS = ["media_player.raspiaudio_muse_luxe"]
SCENARIOS = {
    "busy_timeout_drops_stale_normal_announcement",
    "chime_error_restores_volume",
    "chime_false_is_silent_before_speech",
    "chime_true_precedes_speech",
    "day_volume_applied",
    "default_route_targets_canary",
    "fifo_queue_drains_in_order",
    "night_volume_applied",
    "normal_waits_for_continuous_conversation",
    "normal_waits_for_listening_state",
    "normal_waits_for_music",
    "tts_error_restores_volume",
    "urgent_preempts_busy_audio",
    "urgent_volume_applied",
    "whole_home_route_uses_closed_targets",
}
PLACEHOLDERS = {"pending", "todo", "tbd", "replace", "unknown", "not tested"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Announcement {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"Announcement {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Announcement {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Announcement observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Announcement observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Announcement observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Announcement evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Announcement {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Announcement {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "runtime",
        "metrics",
        "final_state",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Announcement evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Announcement evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    if not isinstance(candidate, dict) or set(candidate) != {
        "device_name",
        "project_version",
        "firmware_sha256",
        "ha_package_sha256",
    }:
        fail("Announcement candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(candidate["ha_package_sha256"], "package SHA-256")
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (package_digest, expected_package_sha256, "HA package SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Announcement {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or runtime != {
        "queue_capacity": 25,
        "normal_wait_timeout_seconds": 600,
        "day_volume": 0.6,
        "night_volume": 0.25,
        "urgent_volume": 0.75,
        "default_targets": TARGETS,
        "whole_home_targets": TARGETS,
    }:
        fail("Announcement runtime differs from the closed contract")

    metrics = evidence["metrics"]
    metric_keys = {
        "successful_deliveries",
        "fifo_messages",
        "normal_wait_cases",
        "urgent_interruptions",
        "busy_timeouts",
        "tts_error_attempts",
        "chime_error_attempts",
        "volume_restore_checks",
        "external_deliveries",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Announcement metrics differ from schema")
    minimums = {
        "successful_deliveries": 10,
        "fifo_messages": 3,
        "normal_wait_cases": 3,
    }
    for name, minimum in minimums.items():
        if type(metrics[name]) is not int or metrics[name] < minimum:
            fail(f"Announcement {name} is below {minimum}")
    for name in (
        "urgent_interruptions",
        "busy_timeouts",
        "tts_error_attempts",
        "chime_error_attempts",
    ):
        if type(metrics[name]) is not int or metrics[name] != 1:
            fail(f"Announcement {name} must equal one")
    successful = metrics["successful_deliveries"]
    restore_checks = metrics["volume_restore_checks"]
    if type(restore_checks) is not int or restore_checks != successful + 2:
        fail("Announcement volume restore checks do not cover success and errors")
    if type(metrics["external_deliveries"]) is not int or metrics["external_deliveries"] != 0:
        fail("Announcement external deliveries must remain zero")

    final_state = evidence["final_state"]
    if not isinstance(final_state, dict) or final_state != {
        "player_state": "idle",
        "voice_state": "waiting",
        "voice_health": "healthy",
        "continuous_conversation": False,
        "queue_drained": True,
    }:
        fail("Announcement final state is not idle and healthy")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Announcement scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
    )
    print(
        "Announcement evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
