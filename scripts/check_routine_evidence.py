#!/usr/bin/env python3
"""Validate candidate-bound physical interactive-routine evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


ROUTINES = [
    "alarm",
    "bedtime",
    "departure",
    "evacuation",
    "power_outage",
    "server_shutdown",
]
SCENARIOS = {
    "active_routine_rejects_second_start",
    "alarm_urgent_chime",
    "cancel_blocked",
    "cancel_paused",
    "cancel_running",
    "departure_manual_guard",
    "disabled_start_rejected",
    "evacuation_urgent_chime",
    "final_reset_clears_identity",
    "ha_restart_paused_persists",
    "ha_restart_running_persists",
    "handoff_preserves_kind",
    "handoff_preserves_session_id",
    "handoff_preserves_step",
    "handoff_second_target_plays",
    "handoff_unavailable_rejected_without_mutation",
    "local_cancel_intent",
    "local_confirm_intent",
    "local_pause_intent",
    "local_resume_intent",
    "local_start_intent",
    "local_status_intent",
    "nonurgent_normal_priority",
    "power_outage_fresh_sensor_verified",
    "power_outage_stale_blocks",
    "same_target_resume",
    "server_shutdown_has_no_control",
    "six_routine_kinds_start",
    "target_missing_rejected",
    "voice_confirmation_cannot_override_stale",
}
PLACEHOLDERS = {"pending", "todo", "tbd", "replace", "unknown", "not tested"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Routine {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"Routine {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        fail(f"Routine {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Routine observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Routine observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed = observed.astimezone(timezone.utc)
    if observed > now + timedelta(minutes=5):
        fail("Routine observed_at is in the future")
    if observed < now - timedelta(days=30):
        fail("Routine evidence is older than 30 days")
    return observed


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Routine {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Routine {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_sentences_sha256: str | None = None,
    expected_live_test_sha256: str | None = None,
    expected_house_package_sha256: str | None = None,
    expected_base_package_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "observed_targets",
        "runtime",
        "metrics",
        "final_state",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Routine evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Routine evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "routine_package_sha256",
        "sentences_sha256",
        "live_test_sha256",
        "house_package_sha256",
        "base_package_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Routine candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    actual = {
        "firmware SHA-256": require_digest(
            candidate["firmware_sha256"], "firmware_sha256"
        ),
        "routine package SHA-256": require_digest(
            candidate["routine_package_sha256"], "routine_package_sha256"
        ),
        "sentences SHA-256": require_digest(
            candidate["sentences_sha256"], "sentences_sha256"
        ),
        "live test SHA-256": require_digest(
            candidate["live_test_sha256"], "live_test_sha256"
        ),
        "house package SHA-256": require_digest(
            candidate["house_package_sha256"], "house_package_sha256"
        ),
        "base package SHA-256": require_digest(
            candidate["base_package_sha256"], "base_package_sha256"
        ),
    }
    expected = {
        "firmware SHA-256": expected_firmware_sha256,
        "routine package SHA-256": expected_package_sha256,
        "sentences SHA-256": expected_sentences_sha256,
        "live test SHA-256": expected_live_test_sha256,
        "house package SHA-256": expected_house_package_sha256,
        "base package SHA-256": expected_base_package_sha256,
    }
    if expected_version is not None and version != expected_version:
        fail("Routine firmware version does not match")
    for label, wanted in expected.items():
        if wanted is not None and actual[label] != wanted:
            fail(f"Routine {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    targets = evidence["observed_targets"]
    if (
        not isinstance(targets, list)
        or len(targets) != 2
        or len(set(targets)) != 2
        or any(
            not isinstance(target, str)
            or re.fullmatch(r"media_player\.[a-z0-9_]+", target) is None
            for target in targets
        )
        or "media_player.raspiaudio_muse_luxe" not in targets
    ):
        fail("Routine handoff requires two distinct observed media players")

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or runtime != {
        "routines": ROUTINES,
        "steps_per_routine": 4,
        "victron_stale_seconds": 300,
        "default_target": "media_player.raspiaudio_muse_luxe",
        "handoff_policy": "explicit_existing_available_media_player",
        "enabled_by_default": False,
        "safety_policy": "guidance_only_no_critical_actions",
    }:
        fail("Routine runtime differs from the closed contract")

    metrics = evidence["metrics"]
    metric_keys = {
        "routine_starts",
        "distinct_targets",
        "handoffs",
        "manual_guard_checks",
        "sensor_verifications",
        "stale_blocks",
        "restart_recoveries",
        "local_intents",
        "session_id_preservation_checks",
        "max_handoff_state_latency_seconds",
        "critical_actions",
        "external_deliveries",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Routine metrics differ from schema")
    minimums = {
        "routine_starts": 6,
        "distinct_targets": 2,
        "handoffs": 2,
        "manual_guard_checks": 2,
        "sensor_verifications": 1,
        "stale_blocks": 1,
        "restart_recoveries": 2,
        "local_intents": 6,
        "session_id_preservation_checks": 2,
    }
    for name, minimum in minimums.items():
        if type(metrics[name]) is not int or metrics[name] < minimum:
            fail(f"Routine {name} is below {minimum}")
    if metrics["distinct_targets"] != len(targets):
        fail("Routine distinct target metric disagrees with observed targets")
    latency = metrics["max_handoff_state_latency_seconds"]
    if type(latency) not in (int, float) or isinstance(latency, bool):
        fail("Routine handoff latency is not numeric")
    if latency <= 0 or latency > 10:
        fail("Routine handoff state latency exceeds ten seconds")
    for name in ("critical_actions", "external_deliveries"):
        if type(metrics[name]) is not int or metrics[name] != 0:
            fail(f"Routine {name} must remain zero")

    final_state = evidence["final_state"]
    final_keys = {
        "enabled",
        "status",
        "kind",
        "verification",
        "step",
        "target",
        "session_id",
        "last_event",
        "player_states",
        "voice_state",
        "voice_health",
    }
    if not isinstance(final_state, dict) or set(final_state) != final_keys:
        fail("Routine final state differs from schema")
    expected_final = {
        "enabled": "off",
        "status": "idle",
        "kind": "none",
        "verification": "none",
        "step": 0,
        "target": "",
        "session_id": "",
        "last_event": "",
        "player_states": {target: "idle" for target in targets},
        "voice_state": "waiting",
        "voice_health": "healthy",
    }
    if final_state != expected_final:
        fail("Routine final state is not fully reset and healthy")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Routine scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-sentences-sha256")
    parser.add_argument("--expected-live-test-sha256")
    parser.add_argument("--expected-house-package-sha256")
    parser.add_argument("--expected-base-package-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_sentences_sha256,
        args.expected_live_test_sha256,
        args.expected_house_package_sha256,
        args.expected_base_package_sha256,
    )
    print(
        "Routine evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])} targets=2."
    )


if __name__ == "__main__":
    main()
