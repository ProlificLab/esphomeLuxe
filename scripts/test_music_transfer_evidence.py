#!/usr/bin/env python3
"""Positive and negative fixtures for two-satellite music evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_music_transfer_evidence import PLAYERS, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
DIGESTS = [character * 64 for character in "abcdef"]


def valid_evidence(version: str = VERSION, *digests: str) -> dict:
    bindings = list(digests) or DIGESTS
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "project_version": version,
            "firmware_sha256": bindings[0],
            "package_sha256": bindings[1],
            "safety_checker_sha256": bindings[2],
            "model_test_sha256": bindings[3],
            "ha_test_sha256": bindings[4],
            "provisioner_sha256": bindings[5],
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "players": list(PLAYERS),
        "runtime": {
            "manual_opt_in_default": "off",
            "minimum_group_minutes": 5,
            "maximum_group_minutes": 240,
            "maximum_group_players": 4,
            "automatic_presence_following": False,
            "recovery_requires_confirmation": True,
        },
        "metrics": {
            "music_each_direction": 2,
            "radio_each_direction": 2,
            "podcast_each_direction": 2,
            "position_samples": 12,
            "maximum_position_drift_seconds": 2.5,
            "playback_state_errors": 0,
            "queue_or_title_errors": 0,
            "volume_samples": 4,
            "maximum_relative_volume_error": 0.02,
            "manual_closes": 2,
            "expiry_closes": 2,
            "ha_restarts": 2,
            "satellite_reboots": 2,
            "join_failure_recoveries": 2,
            "unjoin_failure_recoveries": 2,
            "unavailable_member_rejections": 2,
            "foreign_player_rejections": 2,
            "ghost_groups": 0,
            "automatic_transfers": 0,
            "external_deliveries": 0,
            "cleanup_errors": 0,
        },
        "final_state": {
            "enabled": "off",
            "group_state": "idle",
            "group_master": "",
            "group_members": "",
            "transfer_status": "idle",
            "timer": "idle",
            "player_memberships": {PLAYERS[0]: [], PLAYERS[1]: []},
            "ghost_group": False,
        },
        "scenarios": {
            name: {"passed": True, "evidence": f"Observed {name.replace('_', ' ')} on both Muse players."}
            for name in SCENARIOS
        },
    }


class MusicEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "music.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, VERSION, *DIGESTS)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_every_candidate_binding_is_exact(self) -> None:
        for field in ("project_version", "firmware_sha256", "package_sha256", "safety_checker_sha256", "model_test_sha256", "ha_test_sha256", "provisioner_sha256"):
            evidence = valid_evidence()
            evidence["candidate"][field] = "9" * 64 if field != "project_version" else "other"
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_players_runtime_and_scenarios_are_closed(self) -> None:
        fixtures = []
        evidence = valid_evidence(); evidence["players"].reverse(); fixtures.append(evidence)
        evidence = valid_evidence(); evidence["runtime"]["automatic_presence_following"] = True; fixtures.append(evidence)
        evidence = valid_evidence(); evidence["scenarios"].pop("paused_state_is_preserved"); fixtures.append(evidence)
        evidence = valid_evidence(); evidence["scenarios"]["manual_close_leaves_no_membership"]["evidence"] = "REPLACE"; fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_reject_shortcuts_and_boolean_counts(self) -> None:
        for field, value in (("music_each_direction", 1), ("radio_each_direction", True), ("position_samples", 11), ("maximum_position_drift_seconds", 5.1), ("maximum_relative_volume_error", 0.031), ("manual_closes", 1), ("playback_state_errors", 1), ("ghost_groups", False), ("cleanup_errors", 1)):
            evidence = valid_evidence(); evidence["metrics"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_final_state_must_be_exact_and_empty(self) -> None:
        for field, value in (("enabled", "on"), ("group_state", "review"), ("group_master", PLAYERS[0]), ("ghost_group", True)):
            evidence = valid_evidence(); evidence["final_state"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_stale_future_and_naive_observation_times_fail(self) -> None:
        for value in ((datetime.now(timezone.utc) - timedelta(days=31)).isoformat(), (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat(), datetime.now().replace(tzinfo=None).isoformat()):
            evidence = valid_evidence(); evidence["observed_at"] = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.check(evidence)


if __name__ == "__main__":
    unittest.main()
