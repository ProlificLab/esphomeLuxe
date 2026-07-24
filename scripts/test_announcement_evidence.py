#!/usr/bin/env python3
"""Positive and negative fixtures for physical announcement evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_announcement_evidence import SCENARIOS, TARGETS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
PACKAGE_DIGEST = "b" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    package_digest: str = PACKAGE_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "ha_package_sha256": package_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "queue_capacity": 25,
            "normal_wait_timeout_seconds": 600,
            "day_volume": 0.6,
            "night_volume": 0.25,
            "urgent_volume": 0.75,
            "default_targets": list(TARGETS),
            "whole_home_targets": list(TARGETS),
        },
        "metrics": {
            "successful_deliveries": 10,
            "fifo_messages": 3,
            "normal_wait_cases": 3,
            "urgent_interruptions": 1,
            "busy_timeouts": 1,
            "tts_error_attempts": 1,
            "chime_error_attempts": 1,
            "volume_restore_checks": 12,
            "external_deliveries": 0,
        },
        "final_state": {
            "player_state": "idle",
            "voice_state": "waiting",
            "voice_health": "healthy",
            "continuous_conversation": False,
            "queue_drained": True,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in SCENARIOS
        },
    }


class AnnouncementEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "announcement.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                PACKAGE_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        for field, value in (
            ("project_version", "other"),
            ("firmware_sha256", "c" * 64),
            ("ha_package_sha256", "d" * 64),
        ):
            evidence = valid_evidence()
            evidence["candidate"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_and_final_state_are_exact(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["queue_capacity"] = 100
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["whole_home_targets"] = ["media_player.unknown"]
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["queue_drained"] = False
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("normal_waits_for_music")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["tts_error_restores_volume"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["urgent_preempts_busy_audio"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_are_consistent_and_reject_booleans(self) -> None:
        fixtures = []
        for field, value in (
            ("successful_deliveries", 9),
            ("normal_wait_cases", 2),
            ("urgent_interruptions", True),
            ("busy_timeouts", 0),
            ("volume_restore_checks", 11),
            ("external_deliveries", False),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_stale_or_future_time_fails(self) -> None:
        for delta in (timedelta(days=-31), timedelta(minutes=6)):
            evidence = valid_evidence()
            evidence["observed_at"] = (
                datetime.now(timezone.utc) + delta
            ).isoformat()
            with self.subTest(delta=delta), self.assertRaises(RuntimeError):
                self.check(evidence)


if __name__ == "__main__":
    unittest.main()
