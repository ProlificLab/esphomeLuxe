#!/usr/bin/env python3
"""Unit tests for machine-verifiable endurance evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from monitor_endurance import evaluate_samples, write_summary


def arguments() -> argparse.Namespace:
    return argparse.Namespace(
        max_heap_loss=32768,
        max_psram_loss=131072,
        max_new_errors=0,
        max_new_timeouts=0,
        max_diagnostic_age=180,
    )


def sample(elapsed: float, **changes: object) -> dict:
    values = {
        "timestamp": f"2026-07-22T00:{int(elapsed // 60):02d}:00+00:00",
        "elapsed_seconds": elapsed,
        "diagnostic_age_seconds": 2.0,
        "heap_free": 170000.0,
        "free_psram": 4129000.0,
        "uptime": 1000.0 + elapsed,
        "voice_errors": 0.0,
        "voice_health": "healthy",
        "voice_state": "waiting",
        "voice_timeouts": 0.0,
    }
    values.update(changes)
    return values


class EnduranceEvidenceTests(unittest.TestCase):
    def test_healthy_run_passes(self) -> None:
        device = {
            "name": "muse-luxe",
            "project_version": "2025.3.1-hal.9.0-alpha.2",
        }
        result = evaluate_samples([sample(0), sample(60)], arguments(), device)
        self.assertTrue(result["passed"])
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["device"], device)

    def test_stale_diagnostics_fail(self) -> None:
        result = evaluate_samples(
            [sample(0), sample(240, diagnostic_age_seconds=181)], arguments()
        )
        self.assertFalse(result["passed"])
        self.assertIn("diagnostic age", result["failures"][0])

    def test_reboot_fails(self) -> None:
        result = evaluate_samples(
            [sample(0), sample(60, uptime=12.0)], arguments()
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["uptime_regressions"], 1)

    def test_error_and_memory_regressions_fail(self) -> None:
        result = evaluate_samples(
            [
                sample(0),
                sample(60, heap_free=130000, voice_errors=1, voice_timeouts=1),
            ],
            arguments(),
        )
        self.assertFalse(result["passed"])
        self.assertGreaterEqual(len(result["failures"]), 3)

    def test_summary_write_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            expected = evaluate_samples([sample(0), sample(60)], arguments())
            write_summary(path, expected)
            self.assertEqual(json.loads(path.read_text()), expected)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
