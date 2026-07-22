#!/usr/bin/env python3
"""Validate candidate-bound physical acoustic-guardian evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


LABELS = {"bark", "crying", "fire_alarm", "glass"}
SCENARIOS = {
    "advisory_only_no_physical_action",
    "consent_reviewed",
    "cooldown_deduplicates",
    "cross_check_context_reported",
    "ffprobe_audio_present",
    "four_labels_detected",
    "ha_restart_disables_guardian",
    "mqtt_on_off_observed",
    "no_raw_audio_reaches_muse",
    "private_candidate_validated",
    "retention_one_day_deletes",
    "rollback_audio_status_disabled",
    "transcription_disabled",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Acoustic guardian {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Acoustic guardian {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Acoustic guardian {label} is not a lowercase SHA-256")
    return digest


def parse_time(value: object, label: str, maximum_age_days: int) -> datetime:
    text = require_text(value, label)
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Acoustic guardian {label} is invalid: {error}")
    if observed.tzinfo is None:
        fail(f"Acoustic guardian {label} must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail(f"Acoustic guardian {label} is in the future")
    if observed_utc < now - timedelta(days=maximum_age_days):
        fail(f"Acoustic guardian {label} is too old")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Acoustic guardian {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Acoustic guardian {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def numeric(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"Acoustic guardian {label} must be numeric")
    return float(value)


def validate_label_map(value: object, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != LABELS:
        fail(f"Acoustic guardian {label} differs from the four fixed classes")
    return value


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_preparer_sha256: str | None = None,
    expected_policy_template_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "consent",
        "runtime",
        "metrics",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Acoustic guardian evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Acoustic guardian evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "ha_package_sha256",
        "preparer_sha256",
        "policy_template_sha256",
        "private_frigate_candidate_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Acoustic guardian candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(candidate["ha_package_sha256"], "package SHA-256")
    preparer_digest = require_digest(candidate["preparer_sha256"], "preparer SHA-256")
    policy_digest = require_digest(
        candidate["policy_template_sha256"], "policy template SHA-256"
    )
    require_digest(
        candidate["private_frigate_candidate_sha256"],
        "private Frigate candidate SHA-256",
    )
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (package_digest, expected_package_sha256, "HA package SHA-256"),
        (preparer_digest, expected_preparer_sha256, "preparer SHA-256"),
        (policy_digest, expected_policy_template_sha256, "policy SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Acoustic guardian {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_time(evidence["observed_at"], "observed_at", 30)

    consent = evidence["consent"]
    if not isinstance(consent, dict) or set(consent) != {
        "camera",
        "room",
        "approved_by",
        "approved_at",
    }:
        fail("Acoustic guardian consent differs from schema")
    require_text(consent["camera"], "consent camera", minimum=2)
    require_text(consent["room"], "consent room", minimum=2)
    require_text(consent["approved_by"], "consent approver")
    parse_time(consent["approved_at"], "consent approved_at", 365)

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {
        "thresholds",
        "min_volume",
        "retention_days",
        "transcription_enabled",
        "ha_enabled_after_restart",
    }:
        fail("Acoustic guardian runtime differs from schema")
    thresholds = validate_label_map(runtime["thresholds"], "thresholds")
    for label, threshold in thresholds.items():
        value = numeric(threshold, f"{label} threshold")
        if not 0.80 <= value <= 0.99:
            fail(f"Acoustic guardian {label} threshold is outside policy")
    min_volume = numeric(runtime["min_volume"], "minimum volume")
    if not 200 <= min_volume <= 2000:
        fail("Acoustic guardian minimum volume is outside policy")
    if runtime["retention_days"] != 1:
        fail("Acoustic guardian retention must equal one day")
    if runtime["transcription_enabled"] is not False:
        fail("Acoustic guardian transcription is enabled")
    if runtime["ha_enabled_after_restart"] is not False:
        fail("Acoustic guardian HA opt-in survived restart")

    metrics = evidence["metrics"]
    metric_keys = {
        "observation_hours",
        "test_events",
        "false_positives",
        "idle_cpu_pct",
        "event_cpu_pct",
        "background_rms",
        "event_peak_rms",
        "physical_actions_triggered",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Acoustic guardian metrics differ from schema")
    hours = validate_label_map(metrics["observation_hours"], "observation hours")
    events = validate_label_map(metrics["test_events"], "test events")
    false_positives = validate_label_map(metrics["false_positives"], "false positives")
    for label in LABELS:
        observed_hours = numeric(hours[label], f"{label} observation hours")
        if observed_hours < 2:
            fail(f"Acoustic guardian {label} needs at least two observed hours")
        if type(events[label]) is not int or events[label] < 1:
            fail(f"Acoustic guardian {label} needs a test event")
        if type(false_positives[label]) is not int or false_positives[label] < 0:
            fail(f"Acoustic guardian {label} false positives are invalid")
        if false_positives[label] / observed_hours > 1.0:
            fail(f"Acoustic guardian {label} exceeds one false positive per hour")
    idle_cpu = numeric(metrics["idle_cpu_pct"], "idle CPU")
    event_cpu = numeric(metrics["event_cpu_pct"], "event CPU")
    if not 0 <= idle_cpu <= 100 or not 0 <= event_cpu <= 100:
        fail("Acoustic guardian CPU measurement is outside 0-100 percent")
    if event_cpu - idle_cpu > 30:
        fail("Acoustic guardian event CPU increase exceeds 30 percentage points")
    background_rms = numeric(metrics["background_rms"], "background RMS")
    event_peak_rms = numeric(metrics["event_peak_rms"], "event peak RMS")
    if not 0 <= background_rms < event_peak_rms <= 32767:
        fail("Acoustic guardian RMS measurements are inconsistent")
    if (
        type(metrics["physical_actions_triggered"]) is not int
        or metrics["physical_actions_triggered"] != 0
    ):
        fail("Acoustic guardian triggered a physical action")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Acoustic guardian scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-preparer-sha256")
    parser.add_argument("--expected-policy-template-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_preparer_sha256,
        args.expected_policy_template_sha256,
    )
    print(
        "Acoustic guardian evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
