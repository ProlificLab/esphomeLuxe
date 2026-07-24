#!/usr/bin/env python3
"""Positive and negative fixtures for interactive-routine evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_routine_evidence import ROUTINES, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
DIGESTS = [character * 64 for character in "abcdef"]
TARGETS = [
    "media_player.raspiaudio_muse_luxe",
    "media_player.raspiaudio_muse_luxe_cuisine",
]


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = DIGESTS[0],
    package_digest: str = DIGESTS[1],
    sentences_digest: str = DIGESTS[2],
    live_test_digest: str = DIGESTS[3],
    house_digest: str = DIGESTS[4],
    base_digest: str = DIGESTS[5],
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "routine_package_sha256": package_digest,
            "sentences_sha256": sentences_digest,
            "live_test_sha256": live_test_digest,
            "house_package_sha256": house_digest,
            "base_package_sha256": base_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "observed_targets": list(TARGETS),
        "runtime": {
            "routines": list(ROUTINES),
            "steps_per_routine": 4,
            "victron_stale_seconds": 300,
            "default_target": "media_player.raspiaudio_muse_luxe",
            "handoff_policy": "explicit_existing_available_media_player",
            "enabled_by_default": False,
            "safety_policy": "guidance_only_no_critical_actions",
        },
        "metrics": {
            "routine_starts": 6,
            "distinct_targets": 2,
            "handoffs": 2,
            "manual_guard_checks": 2,
            "sensor_verifications": 1,
            "stale_blocks": 1,
            "restart_recoveries": 2,
            "local_intents": 6,
            "session_id_preservation_checks": 2,
            "max_handoff_state_latency_seconds": 2.5,
            "critical_actions": 0,
            "external_deliveries": 0,
        },
        "final_state": {
            "enabled": "off",
            "status": "idle",
            "kind": "none",
            "verification": "none",
            "step": 0,
            "target": "",
            "session_id": "",
            "last_event": "",
            "player_states": {target: "idle" for target in TARGETS},
            "voice_state": "waiting",
            "voice_health": "healthy",
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on both satellites.",
            }
            for name in SCENARIOS
        },
    }


class RoutineEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "routine.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, VERSION, *DIGESTS)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "routine_package_sha256",
            "sentences_sha256",
            "live_test_sha256",
            "house_package_sha256",
            "base_package_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = (
                "1" * 64 if field != "project_version" else "other"
            )
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_two_distinct_targets_are_required(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["observed_targets"] = [TARGETS[0]]
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["observed_targets"] = [TARGETS[0], TARGETS[0]]
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["observed_targets"][1] = "sensor.not_a_player"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_and_scenarios_are_closed(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["handoff_policy"] = "any_target"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"].pop("handoff_preserves_session_id")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["power_outage_stale_blocks"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["server_shutdown_has_no_control"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_reject_shortcuts_and_booleans(self) -> None:
        for field, value in (
            ("routine_starts", 5),
            ("distinct_targets", True),
            ("handoffs", 1),
            ("manual_guard_checks", 1),
            ("sensor_verifications", 0),
            ("stale_blocks", 0),
            ("restart_recoveries", 1),
            ("local_intents", 5),
            ("session_id_preservation_checks", 1),
            ("max_handoff_state_latency_seconds", 10.1),
            ("critical_actions", False),
            ("external_deliveries", 1),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_final_state_is_exact_and_target_bound(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["final_state"]["enabled"] = "on"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["session_id"] = "leftover"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["player_states"][TARGETS[1]] = "playing"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_stale_future_or_naive_time_fails(self) -> None:
        values = (
            (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
            (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat(),
            datetime.now().replace(tzinfo=None).isoformat(),
        )
        for value in values:
            evidence = valid_evidence()
            evidence["observed_at"] = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.check(evidence)


if __name__ == "__main__":
    unittest.main()
