#!/usr/bin/env python3
"""Validate candidate-bound physical deduplicated video-alert evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


CAMERAS = ["avant_jardin", "sonnette"]
SCENARIOS = {
    "age_30_seconds_is_accepted",
    "after_cooldown_distinct_event_is_announced",
    "announcement_target_is_closed",
    "below_confidence_is_silent",
    "car_label_is_silent",
    "confidence_threshold_is_accepted",
    "cross_camera_cooldown_suppresses_burst",
    "delimiter_event_id_is_silent",
    "disabled_opt_in_is_silent",
    "empty_event_id_is_silent",
    "end_event_type_is_silent",
    "false_positive_is_silent",
    "future_5_seconds_is_accepted",
    "future_6_seconds_is_silent",
    "history_is_fifo_bounded_to_seven",
    "history_survives_ha_restart",
    "long_event_id_is_silent",
    "night_mode_is_silent",
    "normal_priority_is_used",
    "person_event_accepted_on_avant_jardin",
    "person_event_accepted_on_sonnette",
    "same_event_new_is_not_repeated",
    "same_event_update_after_other_event_is_not_repeated",
    "stale_31_seconds_is_silent",
    "unreviewed_camera_is_silent",
    "unreviewed_configured_camera_remains_silent",
    "zones_are_bounded_before_speech",
}
PLACEHOLDERS = {"pending", "todo", "tbd", "replace", "unknown", "not tested"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Video alert {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"Video alert {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        fail(f"Video alert {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Video alert observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Video alert observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed = observed.astimezone(timezone.utc)
    if observed > now + timedelta(minutes=5):
        fail("Video alert observed_at is in the future")
    if observed < now - timedelta(days=30):
        fail("Video alert evidence is older than 30 days")
    return observed


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Video alert {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Video alert {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_base_package_sha256: str | None = None,
    expected_safety_checker_sha256: str | None = None,
    expected_model_test_sha256: str | None = None,
    expected_mqtt_provision_sha256: str | None = None,
    expected_frigate_policy_sha256: str | None = None,
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
        fail("Video alert evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Video alert evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "alert_package_sha256",
        "base_package_sha256",
        "safety_checker_sha256",
        "model_test_sha256",
        "mqtt_provision_sha256",
        "frigate_policy_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Video alert candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    actual = {
        "firmware SHA-256": require_digest(candidate["firmware_sha256"], "firmware_sha256"),
        "alert package SHA-256": require_digest(candidate["alert_package_sha256"], "alert_package_sha256"),
        "base package SHA-256": require_digest(candidate["base_package_sha256"], "base_package_sha256"),
        "safety checker SHA-256": require_digest(candidate["safety_checker_sha256"], "safety_checker_sha256"),
        "model test SHA-256": require_digest(candidate["model_test_sha256"], "model_test_sha256"),
        "MQTT provision SHA-256": require_digest(candidate["mqtt_provision_sha256"], "mqtt_provision_sha256"),
        "Frigate policy SHA-256": require_digest(candidate["frigate_policy_sha256"], "frigate_policy_sha256"),
    }
    expected = {
        "firmware SHA-256": expected_firmware_sha256,
        "alert package SHA-256": expected_package_sha256,
        "base package SHA-256": expected_base_package_sha256,
        "safety checker SHA-256": expected_safety_checker_sha256,
        "model test SHA-256": expected_model_test_sha256,
        "MQTT provision SHA-256": expected_mqtt_provision_sha256,
        "Frigate policy SHA-256": expected_frigate_policy_sha256,
    }
    if expected_version is not None and version != expected_version:
        fail("Video alert firmware version does not match")
    for label, wanted in expected.items():
        if wanted is not None and actual[label] != wanted:
            fail(f"Video alert {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or runtime != {
        "allowed_cameras": CAMERAS,
        "minimum_confidence": 0.75,
        "cooldown_seconds": 60,
        "history_capacity": 7,
        "maximum_event_age_seconds": 30,
        "future_tolerance_seconds": 5,
        "target": "media_player.raspiaudio_muse_luxe",
        "priority": "normal",
        "chime": True,
        "automation_mode": "single",
    }:
        fail("Video alert runtime differs from the closed contract")

    metrics = evidence["metrics"]
    metric_keys = {
        "accepted_announcements",
        "audible_announcements",
        "dedup_rejections",
        "cooldown_rejections",
        "stale_rejections",
        "content_filter_rejections",
        "night_rejections",
        "maximum_history_size",
        "max_delivery_latency_seconds",
        "delivery_errors",
        "critical_actions",
        "external_deliveries",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Video alert metrics differ from schema")
    minimums = {
        "accepted_announcements": 5,
        "dedup_rejections": 2,
        "cooldown_rejections": 1,
        "stale_rejections": 2,
        "content_filter_rejections": 8,
        "night_rejections": 1,
    }
    for name, minimum in minimums.items():
        if type(metrics[name]) is not int or metrics[name] < minimum:
            fail(f"Video alert {name} is below {minimum}")
    accepted = metrics["accepted_announcements"]
    if type(metrics["audible_announcements"]) is not int or metrics["audible_announcements"] != accepted:
        fail("Video alert accepted and audible counts differ")
    if type(metrics["maximum_history_size"]) is not int or metrics["maximum_history_size"] != 7:
        fail("Video alert history did not reach its exact bounded capacity")
    latency = metrics["max_delivery_latency_seconds"]
    if type(latency) not in (int, float) or isinstance(latency, bool) or latency <= 0 or latency > 60:
        fail("Video alert delivery latency exceeds sixty seconds")
    for name in ("delivery_errors", "critical_actions", "external_deliveries"):
        if type(metrics[name]) is not int or metrics[name] != 0:
            fail(f"Video alert {name} must remain zero")

    final_state = evidence["final_state"]
    final_keys = {
        "alerts_enabled",
        "night_mode",
        "mqtt_available",
        "player_state",
        "voice_state",
        "voice_health",
        "history_size",
        "last_event_in_history",
    }
    if not isinstance(final_state, dict) or set(final_state) != final_keys:
        fail("Video alert final state differs from schema")
    if final_state != {
        "alerts_enabled": "off",
        "night_mode": "off",
        "mqtt_available": "on",
        "player_state": "idle",
        "voice_state": "waiting",
        "voice_health": "healthy",
        "history_size": 7,
        "last_event_in_history": True,
    }:
        fail("Video alert final state is not disabled, bounded and healthy")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Video alert scenarios differ from the closed checklist")
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
    parser.add_argument("--expected-safety-checker-sha256")
    parser.add_argument("--expected-model-test-sha256")
    parser.add_argument("--expected-mqtt-provision-sha256")
    parser.add_argument("--expected-frigate-policy-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_base_package_sha256,
        args.expected_safety_checker_sha256,
        args.expected_model_test_sha256,
        args.expected_mqtt_provision_sha256,
        args.expected_frigate_policy_sha256,
    )
    print(
        "Video alert evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
