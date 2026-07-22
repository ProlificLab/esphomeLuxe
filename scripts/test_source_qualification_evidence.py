#!/usr/bin/env python3
"""Positive and negative fixtures for source qualification evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_source_qualification_evidence import validate_evidence


VERSION = "2026.1.0-hal.10-beta.1"
FIRMWARE_SHA = "a" * 64
SOURCE_COMMIT = "b" * 40
SIZE_BYTES = 1888912


def secret_report() -> dict[str, object]:
    return {
        "schema_version": 1,
        "passed": True,
        "tracked_file_count": 180,
        "private_secret_keys_checked": 3,
        "findings": {
            "exact_secret_matches": [],
            "suspicious_pattern_matches": [],
            "prohibited_tracked_files": [],
        },
    }


def ci_report(evidence: dict[str, object]) -> dict[str, object]:
    ci = evidence["ci"]
    return {
        "conclusion": ci["conclusion"],
        "databaseId": ci["run_id"],
        "event": ci["event"],
        "headSha": ci["head_sha"],
        "jobs": [{
            "databaseId": ci["job_id"],
            "name": "compile",
            "status": "completed",
            "conclusion": "success",
        }],
        "name": ci["workflow"],
        "status": "completed",
        "url": ci["url"],
    }


def valid_evidence() -> dict[str, object]:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "project_version": VERSION,
            "firmware_sha256": FIRMWARE_SHA,
            "source_commit": SOURCE_COMMIT,
        },
        "reviewer": "Household release reviewer",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "logs": {},
        "ci": {
            "repository": "ProlificLab/esphomeLuxe",
            "workflow": "Firmware source validation",
            "run_id": 29912173664,
            "job_id": 88897438119,
            "head_sha": SOURCE_COMMIT,
            "conclusion": "success",
            "event": "pull_request",
            "url": "https://github.com/ProlificLab/esphomeLuxe/actions/runs/29912173664",
        },
        "build": {
            "count": 2,
            "first_sha256": FIRMWARE_SHA,
            "second_sha256": FIRMWARE_SHA,
            "reproducible": True,
            "size_bytes": SIZE_BYTES,
            "partition_bytes": 2031616,
            "usage_percent": 92.9,
            "target_percent": 93,
            "hard_percent": 97,
            "hal6_baseline_bytes": 1948144,
            "target_passed": True,
            "hard_limit_passed": True,
            "container_image": "esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0",
            "esp_idf": "5.4.2",
        },
        "secrets_audit": {
            "tracked_file_count": 180,
            "private_secret_keys_checked": 3,
            "exact_secret_matches": 0,
            "suspicious_pattern_matches": 0,
            "prohibited_tracked_files": 0,
        },
    }


def write_log_fixtures(directory: Path, evidence: dict[str, object]) -> None:
    names = ("ci", "build_first", "build_second", "firmware_size", "secrets_audit")
    for name in names:
        path = directory / f"{name}.log"
        if name == "secrets_audit":
            path.write_text(json.dumps(secret_report()), encoding="utf-8")
        elif name == "ci":
            path.write_text(json.dumps(ci_report(evidence)), encoding="utf-8")
        elif name in {"build_first", "build_second"}:
            path.write_text(
                f"reviewed {name} SHA256={evidence['candidate']['firmware_sha256']}\n",
                encoding="utf-8",
            )
        elif name == "firmware_size":
            build = evidence["build"]
            path.write_text(
                f"size_bytes={build['size_bytes']}\n"
                f"partition_bytes={build['partition_bytes']}\n"
                f"usage_percent={build['usage_percent']:.1f}\n"
                f"target_percent={build['target_percent']}\n"
                f"hard_percent={build['hard_percent']}\n"
                f"hal6_baseline_bytes={build['hal6_baseline_bytes']}\n",
                encoding="utf-8",
            )
        else:
            path.write_text(f"reviewed {name} output\n", encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence["logs"][name] = f"sha256:{digest} {path.name}"


class SourceQualificationEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.path = self.directory / "source.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, evidence: dict[str, object]) -> None:
        write_log_fixtures(self.directory, evidence)
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        validate_evidence(
            self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES
        )

    def test_exact_source_record_passes(self) -> None:
        self.validate(valid_evidence())

    def test_candidate_and_ci_identity_drift_fail(self) -> None:
        mutations = (
            ("candidate", "source_commit", "0" * 40),
            ("candidate", "firmware_sha256", "0" * 64),
            ("ci", "head_sha", "0" * 40),
            ("ci", "conclusion", "failure"),
            ("ci", "url", "https://example.invalid/run"),
        )
        for section, field, value in mutations:
            evidence = valid_evidence()
            evidence[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_raw_ci_build_and_size_content_must_match(self) -> None:
        for name in ("ci", "build_first", "firmware_size"):
            evidence = valid_evidence()
            write_log_fixtures(self.directory, evidence)
            log_path = self.directory / f"{name}.log"
            log_path.write_text("reviewed but unrelated\n", encoding="utf-8")
            evidence["logs"][name] = (
                f"sha256:{hashlib.sha256(log_path.read_bytes()).hexdigest()} {log_path.name}"
            )
            self.path.write_text(json.dumps(evidence), encoding="utf-8")
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                validate_evidence(
                    self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES
                )

    def test_reproducibility_and_budget_drift_fail(self) -> None:
        mutations = (
            ("count", 1),
            ("second_sha256", "0" * 64),
            ("reproducible", False),
            ("size_bytes", 1889403),
            ("usage_percent", 93.0),
            ("target_passed", False),
            ("container_image", "esphome/esphome:latest"),
        )
        for field, value in mutations:
            evidence = valid_evidence()
            evidence["build"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_secret_summary_requires_three_real_values_and_no_findings(self) -> None:
        evidence = valid_evidence()
        evidence["secrets_audit"]["private_secret_keys_checked"] = 2
        report = secret_report(); report["private_secret_keys_checked"] = 2
        write_log_fixtures(self.directory, evidence)
        audit_path = self.directory / "secrets_audit.log"
        audit_path.write_text(json.dumps(report), encoding="utf-8")
        evidence["logs"]["secrets_audit"] = (
            f"sha256:{hashlib.sha256(audit_path.read_bytes()).hexdigest()} {audit_path.name}"
        )
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES)

        evidence = valid_evidence()
        evidence["secrets_audit"]["tracked_file_count"] = 1
        write_log_fixtures(self.directory, evidence)
        report = secret_report()
        report["tracked_file_count"] = True
        audit_path.write_text(json.dumps(report), encoding="utf-8")
        evidence["logs"]["secrets_audit"] = (
            f"sha256:{hashlib.sha256(audit_path.read_bytes()).hexdigest()} {audit_path.name}"
        )
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES)

        evidence = valid_evidence()
        write_log_fixtures(self.directory, evidence)
        report = secret_report()
        report["passed"] = False
        report["findings"]["exact_secret_matches"] = [{"key": "x", "path": "y"}]
        audit_path.write_text(json.dumps(report), encoding="utf-8")
        evidence["logs"]["secrets_audit"] = (
            f"sha256:{hashlib.sha256(audit_path.read_bytes()).hexdigest()} {audit_path.name}"
        )
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES)

    def test_tampered_unbound_duplicate_and_escaping_logs_fail(self) -> None:
        evidence = valid_evidence()
        write_log_fixtures(self.directory, evidence)
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        (self.directory / "ci.log").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES)
        for mutation in ("ci.log", "sha256:" + "0" * 64 + " ../escape.log"):
            evidence = valid_evidence()
            write_log_fixtures(self.directory, evidence)
            evidence["logs"]["ci"] = mutation
            self.path.write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES)
        evidence = valid_evidence()
        write_log_fixtures(self.directory, evidence)
        evidence["logs"]["ci"] = evidence["logs"]["build_first"]
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES)

    def test_schema_review_time_and_expected_size_are_closed(self) -> None:
        evidence = valid_evidence(); evidence["extra"] = True
        with self.assertRaises(RuntimeError): self.validate(evidence)
        evidence = valid_evidence(); evidence["reviewed_at"] = "2020-01-01T00:00:00+00:00"
        with self.assertRaises(RuntimeError): self.validate(evidence)
        evidence = valid_evidence()
        write_log_fixtures(self.directory, evidence)
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, SIZE_BYTES + 1)


if __name__ == "__main__":
    unittest.main()
