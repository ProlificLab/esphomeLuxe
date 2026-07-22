#!/usr/bin/env python3
"""Validate candidate-bound physical family-message queue evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


SCENARIOS = {
    "carillon_before_every_delivery",
    "cleared_fields_empty_after_delivery",
    "delivering_restart_moves_to_review",
    "explicit_discard_clears_without_audio",
    "explicit_retry_is_only_replay",
    "five_minute_expiry_is_silent",
    "fourth_message_refused_without_mutation",
    "immediate_message_uses_no_slot",
    "legacy_expired_message_not_extended",
    "legacy_valid_message_migrated_once",
    "normal_restart_preserves_pending_slots",
    "review_never_replays_automatically",
    "reused_low_slot_preserves_fifo",
    "six_minute_stale_claim_moves_to_review",
    "three_slots_store_bounded_transcripts",
    "two_recipients_and_targets_match",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Family message {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"Family message {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Family message {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Family message observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Family message observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Family message observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Family message evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Family message {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Family message {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def exact_int(metrics: dict, name: str, expected: int) -> None:
    if type(metrics[name]) is not int or metrics[name] != expected:
        fail(f"Family message {name} must equal {expected}")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_base_package_sha256: str | None = None,
    expected_provisioner_sha256: str | None = None,
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
        fail("Family message evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Family message evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "message_package_sha256",
        "base_package_sha256",
        "provisioner_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Family message candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(
        candidate["message_package_sha256"], "message package SHA-256"
    )
    base_digest = require_digest(
        candidate["base_package_sha256"], "base package SHA-256"
    )
    provisioner_digest = require_digest(
        candidate["provisioner_sha256"], "provisioner SHA-256"
    )
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (package_digest, expected_package_sha256, "message package SHA-256"),
        (base_digest, expected_base_package_sha256, "base package SHA-256"),
        (provisioner_digest, expected_provisioner_sha256, "provisioner SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Family message {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or runtime != {
        "capacity": 3,
        "maximum_transcript_characters": 240,
        "minimum_expiry_minutes": 5,
        "maximum_expiry_minutes": 1440,
        "review_after_seconds": 360,
        "automatic_delivery": "at_most_once_with_uncertain_quarantine",
        "fixed_target": "media_player.raspiaudio_muse_luxe",
    }:
        fail("Family message runtime differs from the closed contract")

    metrics = evidence["metrics"]
    metric_keys = {
        "distinct_recipients",
        "maximum_observed_transcript_characters",
        "automatic_deliveries",
        "immediate_deliveries",
        "manual_retries",
        "manual_discards",
        "review_quarantines",
        "expired_without_audio",
        "automatic_duplicate_deliveries",
        "audible_deliveries",
        "carillons_heard",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Family message metrics differ from schema")
    if type(metrics["distinct_recipients"]) is not int or metrics["distinct_recipients"] < 2:
        fail("Family message qualification needs two distinct recipients")
    maximum_text = metrics["maximum_observed_transcript_characters"]
    if type(maximum_text) is not int or not 1 <= maximum_text <= 240:
        fail("Family message observed transcript length is outside policy")
    exact_int(metrics, "immediate_deliveries", 1)
    exact_int(metrics, "manual_retries", 1)
    exact_int(metrics, "manual_discards", 1)
    exact_int(metrics, "review_quarantines", 2)
    exact_int(metrics, "expired_without_audio", 1)
    exact_int(metrics, "automatic_duplicate_deliveries", 0)
    automatic = metrics["automatic_deliveries"]
    audible = metrics["audible_deliveries"]
    carillons = metrics["carillons_heard"]
    if type(automatic) is not int or automatic < 3:
        fail("Family message qualification needs at least three automatic deliveries")
    if type(audible) is not int or type(carillons) is not int:
        fail("Family message audible delivery metrics must be integers")
    expected_audible = automatic + 1 + 1
    if audible != expected_audible or carillons != audible:
        fail("Family message audible deliveries and carillons are inconsistent")

    final_state = evidence["final_state"]
    if not isinstance(final_state, dict) or final_state != {
        "slot_1": "empty",
        "slot_2": "empty",
        "slot_3": "empty",
        "transcript_fields_empty": True,
        "legacy_pending": False,
    }:
        fail("Family message final queue state is not empty")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Family message scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-base-package-sha256")
    parser.add_argument("--expected-provisioner-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_base_package_sha256,
        args.expected_provisioner_sha256,
    )
    print(
        "Family message evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
