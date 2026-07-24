#!/usr/bin/env python3
"""Positive and negative fixtures for physical acoustic-guardian evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_acoustic_guardian_evidence import LABELS, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
PACKAGE_DIGEST = "b" * 64
PREPARER_DIGEST = "c" * 64
POLICY_DIGEST = "d" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    package_digest: str = PACKAGE_DIGEST,
    preparer_digest: str = PREPARER_DIGEST,
    policy_digest: str = POLICY_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "ha_package_sha256": package_digest,
            "preparer_sha256": preparer_digest,
            "policy_template_sha256": policy_digest,
            "private_frigate_candidate_sha256": "e" * 64,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "consent": {
            "camera": "sonnette",
            "room": "entree exterieure",
            "approved_by": "Household owner",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
        "runtime": {
            "thresholds": {label: 0.9 for label in LABELS},
            "min_volume": 500,
            "retention_days": 1,
            "transcription_enabled": False,
            "ha_enabled_after_restart": False,
        },
        "metrics": {
            "observation_hours": {label: 2.0 for label in LABELS},
            "test_events": {label: 1 for label in LABELS},
            "false_positives": {label: 1 for label in LABELS},
            "idle_cpu_pct": 20.0,
            "event_cpu_pct": 35.0,
            "background_rms": 400,
            "event_peak_rms": 2400,
            "physical_actions_triggered": 0,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the Chuwi.",
            }
            for name in SCENARIOS
        },
    }


class AcousticGuardianEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "acoustic.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                PACKAGE_DIGEST,
                PREPARER_DIGEST,
                POLICY_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "ha_package_sha256",
            "preparer_sha256",
            "policy_template_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = "other" if field == "project_version" else "f" * 64
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_and_consent_are_closed(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["consent"]["approved_by"] = "REPLACE"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["thresholds"].pop("bark")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["retention_days"] = 2
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["transcription_enabled"] = True
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["ha_enabled_after_restart"] = True
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("transcription_disabled")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["retention_one_day_deletes"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["cooldown_deduplicates"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_are_bounded_and_reject_booleans(self) -> None:
        fixtures = []
        for field, value in (
            ("idle_cpu_pct", True),
            ("event_cpu_pct", 55.0),
            ("event_peak_rms", 300),
            ("physical_actions_triggered", False),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["observation_hours"]["glass"] = 1.9
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["false_positives"]["crying"] = 3
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
