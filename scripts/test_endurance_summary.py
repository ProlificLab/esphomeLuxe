#!/usr/bin/env python3
"""Negative fixtures for 24-hour endurance evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from check_endurance_summary import validate_summary
from monitor_endurance import evaluate_samples, write_summary
from test_monitor_endurance import arguments, sample


VERSION = "2026.1.0-hal.10"


def valid_summary() -> dict:
    samples = [sample(0), sample(86400)]
    result = evaluate_samples(
        samples,
        arguments(),
        {
            "host": "10.10.40.100",
            "name": "muse-luxe",
            "model": "Raspiaudio Muse Luxe",
            "project_name": "prolificlab.muse-luxe",
            "project_version": VERSION,
        },
    )
    finished = datetime.now(timezone.utc) - timedelta(minutes=1)
    result["sample_count"] = 1441
    result["started_at"] = (finished - timedelta(hours=24)).isoformat()
    result["finished_at"] = finished.isoformat()
    return result


class EnduranceSummaryTests(unittest.TestCase):
    def check(self, summary: dict, version: str = VERSION) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            write_summary(path, summary)
            validate_summary(path, version)

    def test_valid_summary_passes(self) -> None:
        self.check(valid_summary())

    def test_short_run_fails(self) -> None:
        summary = valid_summary()
        summary["observed_duration_seconds"] = 86399
        with self.assertRaises(RuntimeError):
            self.check(summary)

    def test_stale_or_rebooted_run_fails(self) -> None:
        for metric, value in (
            ("maximum_diagnostic_age_seconds", 181),
            ("uptime_regressions", 1),
            ("voice_recoveries_delta", 1),
        ):
            summary = deepcopy(valid_summary())
            summary["metrics"][metric] = value
            with self.assertRaises(RuntimeError):
                self.check(summary)

    def test_wrong_firmware_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            self.check(valid_summary(), "2026.1.0-hal.10.1")

    def test_future_or_expired_evidence_fails(self) -> None:
        for offset in (timedelta(minutes=6), -timedelta(days=31)):
            summary = valid_summary()
            finished = datetime.now(timezone.utc) + offset
            summary["started_at"] = (finished - timedelta(hours=24)).isoformat()
            summary["finished_at"] = finished.isoformat()
            with self.subTest(offset=offset), self.assertRaises(RuntimeError):
                self.check(summary)

    def test_failed_summary_fails(self) -> None:
        summary = valid_summary()
        summary["passed"] = False
        summary["failures"] = ["fixture failure"]
        with self.assertRaises(RuntimeError):
            self.check(summary)

    def test_relaxed_threshold_fails(self) -> None:
        for threshold, value in (
            ("max_heap_loss", 999999),
            ("max_new_no_speech", 4),
        ):
            summary = valid_summary()
            summary["thresholds"][threshold] = value
            with self.subTest(threshold=threshold), self.assertRaises(RuntimeError):
                self.check(summary)

    def test_no_speech_limit_is_closed(self) -> None:
        summary = valid_summary()
        summary["metrics"]["voice_no_speech_delta"] = 3
        self.check(summary)
        summary["metrics"]["voice_no_speech_delta"] = 4
        summary["passed"] = False
        summary["failures"] = ["new no-speech sessions 4 > 3"]
        with self.assertRaises(RuntimeError):
            self.check(summary)


if __name__ == "__main__":
    unittest.main()
