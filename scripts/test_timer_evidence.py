#!/usr/bin/env python3
"""Positive and negative fixtures for physical timer evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_timer_evidence import CHECKPOINT_COUNTS, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
BASE_PACKAGE_DIGEST = "b" * 64
TIMER_PACKAGE_DIGEST = "c" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    base_package_digest: str = BASE_PACKAGE_DIGEST,
    timer_package_digest: str = TIMER_PACKAGE_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "base_package_sha256": base_package_digest,
            "timer_package_sha256": timer_package_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "named_timers_created": 2,
            "distinct_timer_names": ["pates", "four"],
            "day_checkpoint_counts": dict(CHECKPOINT_COUNTS),
            "night_checkpoint_counts": dict(CHECKPOINT_COUNTS),
            "replayed_checkpoints_after_reconnect": 0,
            "local_completion_sounds_after_ha_disconnect": 1,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in SCENARIOS
        },
    }


class TimerEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timer.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                BASE_PACKAGE_DIGEST,
                TIMER_PACKAGE_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        mutations = (
            ("project_version", "other-version"),
            ("firmware_sha256", "d" * 64),
            ("base_package_sha256", "e" * 64),
            ("timer_package_sha256", "f" * 64),
        )
        for field, value in mutations:
            evidence = valid_evidence()
            evidence["candidate"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_or_unknown_scenario_fails(self) -> None:
        for mutation in ("missing", "unknown"):
            evidence = valid_evidence()
            if mutation == "missing":
                evidence["scenarios"].pop("pause_resume_each_timer")
            else:
                evidence["scenarios"]["unreviewed"] = evidence["scenarios"][
                    "two_named_timers_visible"
                ]
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"]["reconnect_no_checkpoint_replay"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["music_queue_drains_in_order"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_are_exact_and_names_are_distinct(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["metrics"]["named_timers_created"] = 1
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["distinct_timer_names"] = ["four", "four"]
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["day_checkpoint_counts"]["60"] = 2
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["replayed_checkpoints_after_reconnect"] = 1
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["local_completion_sounds_after_ha_disconnect"] = 0
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
