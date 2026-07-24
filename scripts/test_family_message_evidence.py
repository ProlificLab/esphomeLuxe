#!/usr/bin/env python3
"""Positive and negative fixtures for physical family-message evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_family_message_evidence import SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
PACKAGE_DIGEST = "b" * 64
BASE_DIGEST = "c" * 64
PROVISIONER_DIGEST = "d" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    package_digest: str = PACKAGE_DIGEST,
    base_digest: str = BASE_DIGEST,
    provisioner_digest: str = PROVISIONER_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "message_package_sha256": package_digest,
            "base_package_sha256": base_digest,
            "provisioner_sha256": provisioner_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "capacity": 3,
            "maximum_transcript_characters": 240,
            "minimum_expiry_minutes": 5,
            "maximum_expiry_minutes": 1440,
            "review_after_seconds": 360,
            "automatic_delivery": "at_most_once_with_uncertain_quarantine",
            "fixed_target": "media_player.raspiaudio_muse_luxe",
        },
        "metrics": {
            "distinct_recipients": 2,
            "maximum_observed_transcript_characters": 240,
            "automatic_deliveries": 3,
            "immediate_deliveries": 1,
            "manual_retries": 1,
            "manual_discards": 1,
            "review_quarantines": 2,
            "expired_without_audio": 1,
            "automatic_duplicate_deliveries": 0,
            "audible_deliveries": 5,
            "carillons_heard": 5,
        },
        "final_state": {
            "slot_1": "empty",
            "slot_2": "empty",
            "slot_3": "empty",
            "transcript_fields_empty": True,
            "legacy_pending": False,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} in Home Assistant.",
            }
            for name in SCENARIOS
        },
    }


class FamilyMessageEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "family-message.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                PACKAGE_DIGEST,
                BASE_DIGEST,
                PROVISIONER_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "message_package_sha256",
            "base_package_sha256",
            "provisioner_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = "other" if field == "project_version" else "e" * 64
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_and_final_state_are_exact(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["capacity"] = 4
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["review_after_seconds"] = 30
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["slot_2"] = "review"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("review_never_replays_automatically")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["reused_low_slot_preserves_fifo"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["explicit_retry_is_only_replay"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_are_consistent_and_reject_booleans(self) -> None:
        fixtures = []
        for field, value in (
            ("distinct_recipients", 1),
            ("maximum_observed_transcript_characters", 241),
            ("manual_retries", True),
            ("automatic_duplicate_deliveries", False),
            ("carillons_heard", 4),
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
