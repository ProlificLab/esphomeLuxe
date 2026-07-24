#!/usr/bin/env python3
"""Validate candidate-bound physical two-satellite intercom evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


ROOM_PLAYERS = {
    "bureau": "media_player.raspiaudio_muse_luxe",
    "cuisine": "media_player.muse_luxe_cuisine",
}
DEVICE_ROOMS = {"muse-luxe": "bureau", "muse-luxe-cuisine": "cuisine"}
SCENARIOS = {
    "accept_button_is_target_only",
    "acceptance_chime_precedes_connected_state",
    "bureau_calls_cuisine_explicitly",
    "bureau_reboot_leaves_no_channel",
    "call_chime_and_led_precede_ringing_state",
    "caller_button_cannot_accept",
    "concurrent_call_is_rejected",
    "connected_single_click_starts_manual_listen",
    "cuisine_calls_bureau_explicitly",
    "cuisine_reboot_leaves_no_channel",
    "decline_button_is_target_only",
    "disabled_opt_in_rejects_call",
    "empty_transcript_is_rejected",
    "ha_restart_leaves_no_channel",
    "hangup_button_works_for_each_participant",
    "logbook_omits_transcript_content",
    "music_is_restored_after_intercom",
    "notifications_and_backups_omit_transcripts",
    "old_queued_relay_is_rejected_after_new_session",
    "relay_bureau_to_cuisine_is_audible",
    "relay_cuisine_to_bureau_is_audible",
    "relay_refreshes_five_minute_timeout",
    "ring_timeout_closes_after_45_seconds",
    "same_room_call_is_rejected",
    "session_timeout_closes_after_300_seconds",
    "stale_accept_decline_and_hangup_are_rejected",
    "transcript_241_characters_is_rejected",
    "transcript_is_absent_from_helpers",
    "unknown_player_is_rejected_without_mutation",
    "unavailable_player_is_rejected_without_mutation",
    "urgent_announcement_preempts_intercom_cleanly",
}
PLACEHOLDERS = {"pending", "todo", "tbd", "replace", "unknown", "not tested"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Intercom {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"Intercom {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        fail(f"Intercom {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Intercom observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Intercom observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed = observed.astimezone(timezone.utc)
    if observed > now + timedelta(minutes=5):
        fail("Intercom observed_at is in the future")
    if observed < now - timedelta(days=30):
        fail("Intercom evidence is older than 30 days")
    return observed


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Intercom {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Intercom {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def require_minimum(metrics: dict, name: str, minimum: int) -> int:
    value = metrics[name]
    if type(value) is not int or value < minimum:
        fail(f"Intercom {name} is below {minimum}")
    return value


def require_zero(metrics: dict, name: str) -> None:
    if type(metrics[name]) is not int or metrics[name] != 0:
        fail(f"Intercom {name} must remain zero")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_base_package_sha256: str | None = None,
    expected_sentences_sha256: str | None = None,
    expected_ui_sha256: str | None = None,
    expected_recovery_sha256: str | None = None,
    expected_safety_checker_sha256: str | None = None,
    expected_model_test_sha256: str | None = None,
    expected_ha_test_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "observed_players",
        "observed_devices",
        "runtime",
        "metrics",
        "final_state",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Intercom evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Intercom evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "intercom_package_sha256",
        "base_package_sha256",
        "sentences_sha256",
        "ui_package_sha256",
        "recovery_package_sha256",
        "safety_checker_sha256",
        "model_test_sha256",
        "ha_test_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Intercom candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    actual = {
        "firmware SHA-256": require_digest(candidate["firmware_sha256"], "firmware_sha256"),
        "package SHA-256": require_digest(candidate["intercom_package_sha256"], "intercom_package_sha256"),
        "base package SHA-256": require_digest(candidate["base_package_sha256"], "base_package_sha256"),
        "sentences SHA-256": require_digest(candidate["sentences_sha256"], "sentences_sha256"),
        "UI package SHA-256": require_digest(candidate["ui_package_sha256"], "ui_package_sha256"),
        "recovery package SHA-256": require_digest(candidate["recovery_package_sha256"], "recovery_package_sha256"),
        "safety checker SHA-256": require_digest(candidate["safety_checker_sha256"], "safety_checker_sha256"),
        "model test SHA-256": require_digest(candidate["model_test_sha256"], "model_test_sha256"),
        "HA test SHA-256": require_digest(candidate["ha_test_sha256"], "ha_test_sha256"),
    }
    expected = {
        "firmware SHA-256": expected_firmware_sha256,
        "package SHA-256": expected_package_sha256,
        "base package SHA-256": expected_base_package_sha256,
        "sentences SHA-256": expected_sentences_sha256,
        "UI package SHA-256": expected_ui_sha256,
        "recovery package SHA-256": expected_recovery_sha256,
        "safety checker SHA-256": expected_safety_checker_sha256,
        "model test SHA-256": expected_model_test_sha256,
        "HA test SHA-256": expected_ha_test_sha256,
    }
    if expected_version is not None and version != expected_version:
        fail("Intercom firmware version does not match")
    for label, wanted in expected.items():
        if wanted is not None and actual[label] != wanted:
            fail(f"Intercom {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    if evidence["observed_players"] != list(ROOM_PLAYERS.values()):
        fail("Intercom observed players differ from the closed room map")
    if evidence["observed_devices"] != list(DEVICE_ROOMS):
        fail("Intercom observed devices differ from the trusted button map")

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or runtime != {
        "room_players": ROOM_PLAYERS,
        "device_rooms": DEVICE_ROOMS,
        "ring_timeout_seconds": 45,
        "session_timeout_seconds": 300,
        "maximum_transcript_characters": 240,
        "relay_queue_capacity": 5,
        "transport": "transcribed_push_to_talk",
        "origin_policy": "explicit_room_or_trusted_device_event",
        "single_click": "accept_or_manual_listen",
        "double_click": "decline_or_hangup",
        "raw_audio": False,
        "duplex": False,
    }:
        fail("Intercom runtime differs from the closed contract")

    metrics = evidence["metrics"]
    metric_keys = {
        "calls_bureau_to_cuisine",
        "calls_cuisine_to_bureau",
        "accepted_calls",
        "declined_calls",
        "participant_hangups",
        "ring_timeouts",
        "session_timeouts",
        "relays_bureau_to_cuisine",
        "relays_cuisine_to_bureau",
        "button_actions",
        "session_mismatch_rejections",
        "unavailable_player_rejections",
        "audible_actions",
        "carillons_heard",
        "visible_led_signals",
        "relay_attempts",
        "recognition_errors",
        "recognition_error_rate",
        "p95_transcript_to_speech_latency_seconds",
        "max_transcript_to_speech_latency_seconds",
        "ghost_channels",
        "raw_audio_sessions",
        "transcript_artifacts",
        "external_deliveries",
        "music_restore_errors",
        "urgent_preemption_errors",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Intercom metrics differ from schema")
    calls_a = require_minimum(metrics, "calls_bureau_to_cuisine", 20)
    calls_b = require_minimum(metrics, "calls_cuisine_to_bureau", 20)
    accepted = require_minimum(metrics, "accepted_calls", 8)
    declined = require_minimum(metrics, "declined_calls", 4)
    hangups = require_minimum(metrics, "participant_hangups", 4)
    ring_timeouts = require_minimum(metrics, "ring_timeouts", 2)
    session_timeouts = require_minimum(metrics, "session_timeouts", 2)
    relays_a = require_minimum(metrics, "relays_bureau_to_cuisine", 10)
    relays_b = require_minimum(metrics, "relays_cuisine_to_bureau", 10)
    require_minimum(metrics, "button_actions", 4)
    require_minimum(metrics, "session_mismatch_rejections", 4)
    require_minimum(metrics, "unavailable_player_rejections", 3)
    audible = require_minimum(
        metrics,
        "audible_actions",
        calls_a
        + calls_b
        + accepted * 2
        + relays_a
        + relays_b
        + declined
        + hangups * 2
        + (ring_timeouts + session_timeouts) * 2,
    )
    if metrics["carillons_heard"] != audible or metrics["visible_led_signals"] != audible:
        fail("Intercom audible, carillon and visible LED counts differ")
    attempts = require_minimum(metrics, "relay_attempts", relays_a + relays_b)
    errors = metrics["recognition_errors"]
    rate = metrics["recognition_error_rate"]
    if type(errors) is not int or not 0 <= errors <= attempts:
        fail("Intercom recognition_errors is invalid")
    if attempts - errors != relays_a + relays_b:
        fail("Intercom relay attempts, errors and audible deliveries differ")
    if type(rate) not in (int, float) or isinstance(rate, bool):
        fail("Intercom recognition_error_rate is invalid")
    expected_rate = errors / attempts
    if abs(rate - expected_rate) > 0.0001 or rate > 0.10:
        fail("Intercom recognition error rate exceeds ten percent")
    p95 = metrics["p95_transcript_to_speech_latency_seconds"]
    maximum = metrics["max_transcript_to_speech_latency_seconds"]
    for value, label in ((p95, "p95 latency"), (maximum, "maximum latency")):
        if type(value) not in (int, float) or isinstance(value, bool) or value <= 0:
            fail(f"Intercom {label} is invalid")
    if p95 > 15 or maximum > 30 or maximum < p95:
        fail("Intercom transcript-to-speech latency exceeds policy")
    for name in (
        "ghost_channels",
        "raw_audio_sessions",
        "transcript_artifacts",
        "external_deliveries",
        "music_restore_errors",
        "urgent_preemption_errors",
    ):
        require_zero(metrics, name)

    final_state = evidence["final_state"]
    if not isinstance(final_state, dict) or final_state != {
        "enabled": "off",
        "status": "idle",
        "caller_room": "",
        "target_room": "",
        "session_id": "",
        "last_event": "",
        "ring_timer": "idle",
        "session_timer": "idle",
        "player_states": {
            "media_player.raspiaudio_muse_luxe": "idle",
            "media_player.muse_luxe_cuisine": "idle",
        },
        "voice_states": {"muse-luxe": "waiting", "muse-luxe-cuisine": "waiting"},
        "voice_health": {"muse-luxe": "healthy", "muse-luxe-cuisine": "healthy"},
        "music_restored": True,
        "active_channel": False,
    }:
        fail("Intercom final state is not empty, disabled and healthy")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Intercom scenarios differ from the closed checklist")
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
    parser.add_argument("--expected-sentences-sha256")
    parser.add_argument("--expected-ui-sha256")
    parser.add_argument("--expected-recovery-sha256")
    parser.add_argument("--expected-safety-checker-sha256")
    parser.add_argument("--expected-model-test-sha256")
    parser.add_argument("--expected-ha-test-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_base_package_sha256,
        args.expected_sentences_sha256,
        args.expected_ui_sha256,
        args.expected_recovery_sha256,
        args.expected_safety_checker_sha256,
        args.expected_model_test_sha256,
        args.expected_ha_test_sha256,
    )
    print(
        "Intercom evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
