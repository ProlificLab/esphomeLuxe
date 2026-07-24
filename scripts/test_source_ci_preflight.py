#!/usr/bin/env python3
"""Offline fixtures for exact source-CI preflight."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from check_source_ci_preflight import validate


COMMIT = "b" * 40


def valid_report() -> dict[str, object]:
    return {
        "conclusion": "success",
        "databaseId": 29918098929,
        "event": "pull_request",
        "headSha": COMMIT,
        "jobs": [{"databaseId": 88916611436, "name": "compile",
                  "status": "completed", "conclusion": "success"}],
        "name": "Firmware source validation",
        "status": "completed",
        "url": "https://github.com/ProlificLab/esphomeLuxe/actions/runs/29918098929",
    }


class SourceCiPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "ci.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, report: dict[str, object]) -> None:
        self.path.write_text(json.dumps(report), encoding="utf-8")

    def test_exact_successful_run_passes_with_safe_identity(self) -> None:
        self.write(valid_report())
        result = validate(self.path, COMMIT)
        self.assertEqual(result["run_id"], 29918098929)
        self.assertEqual(set(result), {"schema_version", "passed", "run_id", "job_id", "head_sha"})

    def test_commit_run_url_and_conclusion_drift_fail(self) -> None:
        for field, value in (
            ("headSha", "0" * 40),
            ("databaseId", True),
            ("url", "https://example.invalid/run"),
            ("conclusion", "failure"),
            ("status", "in_progress"),
        ):
            report = valid_report(); report[field] = value; self.write(report)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate(self.path, COMMIT)

    def test_compile_job_must_be_unique_completed_and_successful(self) -> None:
        mutations = []
        report = valid_report(); report["jobs"] = []; mutations.append(report)
        report = valid_report(); report["jobs"] = report["jobs"] * 2; mutations.append(report)
        report = valid_report(); report["jobs"][0]["conclusion"] = "failure"; mutations.append(report)
        report = valid_report(); report["jobs"][0]["databaseId"] = False; mutations.append(report)
        for index, report in enumerate(mutations):
            self.write(report)
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                validate(self.path, COMMIT)

    def test_schema_and_expected_commit_are_closed(self) -> None:
        report = valid_report(); report["extra"] = True; self.write(report)
        with self.assertRaises(RuntimeError): validate(self.path, COMMIT)
        self.write(valid_report())
        with self.assertRaises(RuntimeError): validate(self.path, "short")
        self.path.write_text("not-json", encoding="utf-8")
        with self.assertRaises(RuntimeError): validate(self.path, COMMIT)


if __name__ == "__main__":
    unittest.main()
