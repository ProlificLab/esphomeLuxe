#!/usr/bin/env python3
"""Validate candidate-bound physical two-satellite music transfer evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


PLAYERS = [
    "media_player.raspiaudio_muse_luxe_2",
    "media_player.raspiaudio_muse_luxe_kitchen",
]
SCENARIOS = {
    "disabled_opt_in_rejects_transfer",
    "foreign_player_is_rejected",
    "music_transfers_both_directions",
    "radio_transfers_both_directions",
    "podcast_transfers_both_directions",
    "title_queue_position_and_play_state_are_preserved",
    "paused_state_is_preserved",
    "relative_volumes_survive_group_creation",
    "manual_close_leaves_no_membership",
    "expiry_close_leaves_no_membership",
    "ha_restart_preserves_active_group_with_timer",
    "lost_timer_enters_review",
    "join_failure_enters_review",
    "unjoin_failure_enters_review",
    "unavailable_member_blocks_false_cleanup",
    "confirmed_recovery_clears_all_members",
    "transfer_is_blocked_during_group_or_review",
    "satellite_reboots_leave_no_ghost_group",
}
PLACEHOLDERS = {"pending", "todo", "tbd", "replace", "unknown", "not tested"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Music transfer {label} is missing or too short")
    result = value.strip()
    if result.lower() in PLACEHOLDERS:
        fail(f"Music transfer {label} is still a placeholder")
    return result


def digest(value: object, label: str) -> str:
    result = text(value, label, 64)
    if re.fullmatch(r"[0-9a-f]{64}", result) is None:
        fail(f"Music transfer {label} is not a lowercase SHA-256")
    return result


def observed_at(value: object) -> None:
    try:
        observed = datetime.fromisoformat(text(value, "observed_at").replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Music transfer observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Music transfer observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed = observed.astimezone(timezone.utc)
    if observed > now + timedelta(minutes=5) or observed < now - timedelta(days=30):
        fail("Music transfer evidence time is outside the 30-day window")


def minimum(metrics: dict, name: str, required: int) -> int:
    value = metrics.get(name)
    if type(value) is not int or value < required:
        fail(f"Music transfer {name} is below {required}")
    return value


def zero(metrics: dict, name: str) -> None:
    if type(metrics.get(name)) is not int or metrics[name] != 0:
        fail(f"Music transfer {name} must remain zero")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_safety_checker_sha256: str | None = None,
    expected_model_test_sha256: str | None = None,
    expected_ha_test_sha256: str | None = None,
    expected_provisioner_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    keys = {"schema_version", "passed", "candidate", "observer", "observed_at", "players", "runtime", "metrics", "final_state", "scenarios"}
    if not isinstance(evidence, dict) or set(evidence) != keys:
        fail("Music transfer evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Music transfer evidence did not pass with schema version 1")
    candidate = evidence["candidate"]
    candidate_keys = {"project_version", "firmware_sha256", "package_sha256", "safety_checker_sha256", "model_test_sha256", "ha_test_sha256", "provisioner_sha256"}
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Music transfer candidate identity is incomplete")
    version = text(candidate["project_version"], "project_version")
    actual = [
        digest(candidate["firmware_sha256"], "firmware_sha256"),
        digest(candidate["package_sha256"], "package_sha256"),
        digest(candidate["safety_checker_sha256"], "safety_checker_sha256"),
        digest(candidate["model_test_sha256"], "model_test_sha256"),
        digest(candidate["ha_test_sha256"], "ha_test_sha256"),
        digest(candidate["provisioner_sha256"], "provisioner_sha256"),
    ]
    expected = [expected_firmware_sha256, expected_package_sha256, expected_safety_checker_sha256, expected_model_test_sha256, expected_ha_test_sha256, expected_provisioner_sha256]
    if expected_version is not None and version != expected_version:
        fail("Music transfer version does not match")
    if any(wanted is not None and got != wanted for got, wanted in zip(actual, expected)):
        fail("Music transfer candidate source binding does not match")
    text(evidence["observer"], "observer")
    observed_at(evidence["observed_at"])
    if evidence["players"] != PLAYERS:
        fail("Music transfer players differ from the closed two-satellite map")
    if evidence["runtime"] != {"manual_opt_in_default": "off", "minimum_group_minutes": 5, "maximum_group_minutes": 240, "maximum_group_players": 4, "automatic_presence_following": False, "recovery_requires_confirmation": True}:
        fail("Music transfer runtime differs from the closed contract")
    metrics = evidence["metrics"]
    metric_keys = {"music_each_direction", "radio_each_direction", "podcast_each_direction", "position_samples", "maximum_position_drift_seconds", "playback_state_errors", "queue_or_title_errors", "volume_samples", "maximum_relative_volume_error", "manual_closes", "expiry_closes", "ha_restarts", "satellite_reboots", "join_failure_recoveries", "unjoin_failure_recoveries", "unavailable_member_rejections", "foreign_player_rejections", "ghost_groups", "automatic_transfers", "external_deliveries", "cleanup_errors"}
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Music transfer metrics differ from schema")
    for name in ("music_each_direction", "radio_each_direction", "podcast_each_direction"):
        minimum(metrics, name, 2)
    minimum(metrics, "position_samples", 12)
    minimum(metrics, "volume_samples", 4)
    for name in ("manual_closes", "expiry_closes", "ha_restarts", "satellite_reboots", "join_failure_recoveries", "unjoin_failure_recoveries", "unavailable_member_rejections", "foreign_player_rejections"):
        minimum(metrics, name, 2)
    drift = metrics["maximum_position_drift_seconds"]
    volume_error = metrics["maximum_relative_volume_error"]
    if type(drift) not in (int, float) or isinstance(drift, bool) or not 0 <= drift <= 5:
        fail("Music transfer position drift exceeds five seconds")
    if type(volume_error) not in (int, float) or isinstance(volume_error, bool) or not 0 <= volume_error <= 0.03:
        fail("Music transfer relative volume error exceeds 0.03")
    for name in ("playback_state_errors", "queue_or_title_errors", "ghost_groups", "automatic_transfers", "external_deliveries", "cleanup_errors"):
        zero(metrics, name)
    final = evidence["final_state"]
    if final != {"enabled": "off", "group_state": "idle", "group_master": "", "group_members": "", "transfer_status": "idle", "timer": "idle", "player_memberships": {PLAYERS[0]: [], PLAYERS[1]: []}, "ghost_group": False}:
        fail("Music transfer final state is not empty, disabled and ungrouped")
    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Music transfer scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        if not isinstance(result, dict) or set(result) != {"passed", "evidence"} or result["passed"] is not True:
            fail(f"Music transfer scenario {name} did not pass")
        text(result["evidence"], f"scenario {name} evidence")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    for name in ("version", "firmware-sha256", "package-sha256", "safety-checker-sha256", "model-test-sha256", "ha-test-sha256", "provisioner-sha256"):
        parser.add_argument(f"--expected-{name}")
    args = parser.parse_args()
    evidence = validate_evidence(args.evidence, args.expected_version, args.expected_firmware_sha256, args.expected_package_sha256, args.expected_safety_checker_sha256, args.expected_model_test_sha256, args.expected_ha_test_sha256, args.expected_provisioner_sha256)
    print(f"Music transfer evidence passed: version={evidence['candidate']['project_version']} scenarios={len(evidence['scenarios'])}.")


if __name__ == "__main__":
    main()
