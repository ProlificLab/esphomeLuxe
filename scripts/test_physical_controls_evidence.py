#!/usr/bin/env python3
"""Positive and negative physical control evidence fixtures."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_physical_controls_evidence import OBSERVATIONS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
DIGEST = "a" * 64


def valid_evidence(version: str = VERSION, digest: str = DIGEST) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "hardware": "Raspiaudio Muse Luxe ESP32-S3",
            "project_version": version,
            "firmware_sha256": digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "location": "Bureau",
        "observations": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in OBSERVATIONS
        },
    }


class PhysicalControlsEvidenceTests(unittest.TestCase):
    def check(
        self,
        evidence: dict,
        version: str = VERSION,
        digest: str = DIGEST,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "physical-controls.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, version, digest)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_wrong_version_or_hash_fails(self) -> None:
        for version, digest in (("wrong-version", DIGEST), (VERSION, "b" * 64)):
            with self.subTest(version=version, digest=digest), self.assertRaises(
                RuntimeError
            ):
                self.check(valid_evidence(version, digest))

    def test_missing_or_unknown_observation_fails(self) -> None:
        for mutation in ("missing", "unknown"):
            evidence = valid_evidence()
            if mutation == "missing":
                evidence["observations"].pop("single_press_mute")
            else:
                evidence["observations"]["unreviewed_gesture"] = {
                    "passed": True,
                    "evidence": "Unexpected observation must fail closed.",
                }
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_false_or_placeholder_observation_fails(self) -> None:
        for field, value in (("passed", False), ("evidence", "REPLACE")):
            evidence = valid_evidence()
            evidence["observations"]["long_press_privacy"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_stale_or_future_timestamp_fails(self) -> None:
        for delta in (timedelta(days=-31), timedelta(minutes=6)):
            evidence = valid_evidence()
            evidence["observed_at"] = (
                datetime.now(timezone.utc) + delta
            ).isoformat()
            with self.subTest(delta=delta), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_malformed_candidate_or_digest_fails(self) -> None:
        evidence = valid_evidence()
        evidence["candidate"] = deepcopy(evidence["candidate"])
        evidence["candidate"]["firmware_sha256"] = "A" * 64
        with self.assertRaises(RuntimeError):
            self.check(evidence, digest="A" * 64)


if __name__ == "__main__":
    unittest.main()
