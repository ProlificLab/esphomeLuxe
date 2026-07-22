#!/usr/bin/env python3
"""Negative fixtures for 24-hour endurance evidence."""

from __future__ import annotations

from copy import deepcopy
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
    result["sample_count"] = 1441
    result["finished_at"] = "2026-07-23T00:00:00+00:00"
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
        ):
            summary = deepcopy(valid_summary())
            summary["metrics"][metric] = value
            with self.assertRaises(RuntimeError):
                self.check(summary)

    def test_wrong_firmware_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            self.check(valid_summary(), "2026.1.0-hal.10.1")

    def test_failed_summary_fails(self) -> None:
        summary = valid_summary()
        summary["passed"] = False
        summary["failures"] = ["fixture failure"]
        with self.assertRaises(RuntimeError):
            self.check(summary)

    def test_relaxed_threshold_fails(self) -> None:
        summary = valid_summary()
        summary["thresholds"]["max_heap_loss"] = 999999
        with self.assertRaises(RuntimeError):
            self.check(summary)


if __name__ == "__main__":
    unittest.main()
