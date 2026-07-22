#!/usr/bin/env python3
"""Positive and negative fixtures for hal.9 mode evidence."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from check_hal9_modes_evidence import validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"


def valid_evidence() -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "device": {
            "host": "10.10.40.100",
            "name": "muse-luxe",
            "model": "Raspiaudio Muse Luxe",
            "project_name": "raspiaudio.voice-assistant",
            "project_version": VERSION,
        },
        "started_at": "2026-07-23T08:00:00+00:00",
        "finished_at": "2026-07-23T08:01:00+00:00",
        "cases": [
            {"name": "privacy_on", "observed_at": "2026-07-23T08:00:10+00:00", "privacy_mode": True, "continuous_conversation": False, "voice_state": "privacy", "voice_health": "privacy"},
            {"name": "privacy_off", "observed_at": "2026-07-23T08:00:20+00:00", "privacy_mode": False, "continuous_conversation": False, "voice_state": "waiting", "voice_health": "healthy"},
            {"name": "continuous_on", "observed_at": "2026-07-23T08:00:30+00:00", "privacy_mode": False, "continuous_conversation": True, "voice_state": "listening", "voice_health": "healthy"},
            {"name": "continuous_off", "observed_at": "2026-07-23T08:00:40+00:00", "privacy_mode": False, "continuous_conversation": False, "voice_state": "waiting", "voice_health": "healthy"},
        ],
        "diagnostics_before": {"voice_errors": 0.0, "voice_timeouts": 0.0, "voice_recoveries": 0.0},
        "diagnostics_after": {"voice_errors": 0.0, "voice_timeouts": 0.0, "voice_recoveries": 0.0},
        "cleanup": {"observed_at": "2026-07-23T08:00:50+00:00", "privacy_mode": False, "continuous_conversation": False, "voice_state": "waiting", "voice_health": "healthy"},
    }


class ModesEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict, version: str = VERSION) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "modes.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, version)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_wrong_version_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            self.check(valid_evidence(), "2025.3.1-hal.9.0-alpha.6")

    def test_missing_or_reordered_case_fails(self) -> None:
        for cases in (
            valid_evidence()["cases"][:-1],
            list(reversed(valid_evidence()["cases"])),
        ):
            evidence = valid_evidence()
            evidence["cases"] = cases
            with self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_wrong_mode_state_fails(self) -> None:
        evidence = valid_evidence()
        evidence["cases"][2]["continuous_conversation"] = False
        with self.assertRaises(RuntimeError):
            self.check(evidence)

    def test_changed_diagnostics_fail(self) -> None:
        evidence = valid_evidence()
        evidence["diagnostics_after"]["voice_timeouts"] = 1.0
        with self.assertRaises(RuntimeError):
            self.check(evidence)

    def test_malformed_diagnostics_fail_closed(self) -> None:
        evidence = valid_evidence()
        evidence["diagnostics_after"] = None
        with self.assertRaises(RuntimeError):
            self.check(evidence)

    def test_non_finite_diagnostics_fail(self) -> None:
        for value in (float("nan"), float("inf"), True):
            evidence = valid_evidence()
            evidence["diagnostics_before"]["voice_errors"] = value
            evidence["diagnostics_after"]["voice_errors"] = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_unsafe_cleanup_fails(self) -> None:
        evidence = valid_evidence()
        evidence["cleanup"]["continuous_conversation"] = True
        with self.assertRaises(RuntimeError):
            self.check(evidence)

    def test_cleanup_timestamp_out_of_order_fails(self) -> None:
        evidence = valid_evidence()
        evidence["cleanup"]["observed_at"] = "2026-07-23T07:59:00+00:00"
        with self.assertRaises(RuntimeError):
            self.check(evidence)

    def test_non_monotonic_timestamps_fail(self) -> None:
        evidence = deepcopy(valid_evidence())
        evidence["cases"][1]["observed_at"] = "2026-07-23T07:59:00+00:00"
        with self.assertRaises(RuntimeError):
            self.check(evidence)


if __name__ == "__main__":
    unittest.main()
