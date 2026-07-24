#!/usr/bin/env python3
"""Positive and negative fixtures for day/night LED evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_night_led_evidence import PROFILES, SCENARIOS, validate_evidence


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
        "profiles": {
            name: {
                "passed": True,
                "day_brightness_pct": values[0],
                "night_brightness_pct": values[1],
                "evidence": f"Observed {name} day and night on the canary.",
            }
            for name, values in PROFILES.items()
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in SCENARIOS
        },
    }


class NightLedEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "night-led.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, VERSION, FIRMWARE_DIGEST, PACKAGE_DIGEST)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        mutations = (
            ("project_version", "other-version"),
            ("firmware_sha256", "c" * 64),
            ("ha_package_sha256", "d" * 64),
        )
        for field, value in mutations:
            evidence = valid_evidence()
            evidence["candidate"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_or_unknown_phase_fails(self) -> None:
        for mutation in ("missing", "unknown"):
            evidence = valid_evidence()
            if mutation == "missing":
                evidence["profiles"].pop("privacy")
            else:
                evidence["profiles"]["unmapped"] = evidence["profiles"]["waiting"]
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_wrong_brightness_or_false_phase_fails(self) -> None:
        evidence = valid_evidence()
        evidence["profiles"]["listening"]["night_brightness_pct"] = 5
        with self.assertRaises(RuntimeError):
            self.check(evidence)
        evidence = valid_evidence()
        evidence["profiles"]["rescue"]["passed"] = False
        with self.assertRaises(RuntimeError):
            self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("timer_day_night_transition")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["privacy_visible_at_night"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["waiting_api_day_night_restore"]["evidence"] = "REPLACE"
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
