#!/usr/bin/env python3
"""Offline tests for atomic source-qualification sealing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from seal_source_qualification_evidence import derive_record, seal


VERSION = "2026.1.0-hal.10-beta.1"
COMMIT = "b" * 40


class SealSourceQualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifact = self.root / "candidate.ota.bin"
        self.artifact.write_bytes(b"x" * 1888912)
        self.sha = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.output = self.root / "source.json"
        self.secrets = self.root / "secrets.yaml"
        self.secrets.write_text(
            "api_encryption_key: real-private-api-value\n"
            "ota_password: real-private-ota-value\n"
            "fallback_ap_password: real-private-ap-value\n",
            encoding="utf-8",
        )
        self.secrets.chmod(0o600)
        self.secrets_sha = hashlib.sha256(self.secrets.read_bytes()).hexdigest()
        self.write_logs()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_logs(self) -> None:
        ci = {
            "conclusion": "success", "databaseId": 123, "event": "pull_request",
            "headSha": COMMIT, "jobs": [{"databaseId": 456, "name": "compile",
            "status": "completed", "conclusion": "success"}],
            "name": "Firmware source validation", "status": "completed",
            "url": "https://github.com/ProlificLab/esphomeLuxe/actions/runs/123",
        }
        (self.root / "ci.log").write_text(json.dumps(ci), encoding="utf-8")
        for name in ("build-first.log", "build-second.log"):
            (self.root / name).write_text(
                f"SECRETS SHA256={self.secrets_sha}\nOTA SHA256={self.sha}\n",
                encoding="utf-8",
            )
        (self.root / "firmware-size.log").write_text(
            "size_bytes=1888912\npartition_bytes=2031616\nusage_percent=92.9\n"
            "target_percent=93\nhard_percent=97\nhal6_baseline_bytes=1948144\n",
            encoding="utf-8",
        )
        audit = {"schema_version": 1, "passed": True, "tracked_file_count": 335,
                 "private_secret_keys_checked": 3, "findings": {
                 "exact_secret_matches": [], "suspicious_pattern_matches": [],
                 "prohibited_tracked_files": []}}
        (self.root / "secrets-audit.log").write_text(json.dumps(audit), encoding="utf-8")

    def derive(self) -> dict[str, object]:
        return derive_record(self.output, self.root, self.artifact, VERSION, COMMIT,
                             "Household release reviewer", self.secrets)

    def test_derives_and_atomically_seals_exact_record(self) -> None:
        record = self.derive(); seal(record, self.output)
        sealed = json.loads(self.output.read_text())
        self.assertTrue(sealed["passed"])
        self.assertEqual(sealed["candidate"]["firmware_sha256"], self.sha)
        self.assertEqual(sealed["ci"]["run_id"], 123)
        self.assertEqual(sealed["credentials"]["file_sha256"], self.secrets_sha)
        self.assertEqual(sealed["secrets_audit"]["private_secret_keys_checked"], 3)

    def test_refuses_existing_output_without_modification(self) -> None:
        self.output.write_text("keep", encoding="utf-8")
        with self.assertRaises(RuntimeError): self.derive()
        self.assertEqual(self.output.read_text(), "keep")

    def test_ci_and_build_identity_drift_fail(self) -> None:
        ci_path = self.root / "ci.log"
        ci = json.loads(ci_path.read_text()); ci["headSha"] = "0" * 40
        ci_path.write_text(json.dumps(ci), encoding="utf-8")
        with self.assertRaises(RuntimeError): seal(self.derive(), self.output)
        self.write_logs()
        (self.root / "build-second.log").write_text("different build\n", encoding="utf-8")
        with self.assertRaises(RuntimeError): self.derive()

    def test_size_and_secret_findings_fail(self) -> None:
        (self.root / "firmware-size.log").write_text("size_bytes=1\n", encoding="utf-8")
        with self.assertRaises(RuntimeError): self.derive()
        self.write_logs()
        audit_path = self.root / "secrets-audit.log"
        audit = json.loads(audit_path.read_text()); audit["passed"] = False
        audit["findings"]["exact_secret_matches"] = [{"key": "x", "path": "y"}]
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        with self.assertRaises(RuntimeError): seal(self.derive(), self.output)

    def test_external_logs_fail(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        try:
            with self.assertRaises(RuntimeError):
                derive_record(self.output, outside, self.artifact, VERSION, COMMIT,
                              "Household release reviewer", self.secrets)
        finally:
            outside.rmdir()
        log = self.root / "build-second.log"
        log.unlink(); log.symlink_to(self.root / "build-first.log")
        with self.assertRaises(RuntimeError): self.derive()

    def test_private_secrets_and_both_build_bindings_are_mandatory(self) -> None:
        self.secrets.chmod(0o644)
        with self.assertRaises(RuntimeError): self.derive()
        self.secrets.chmod(0o600)
        (self.root / "build-first.log").write_text(
            f"OTA SHA256={self.sha}\n", encoding="utf-8"
        )
        with self.assertRaises(RuntimeError): self.derive()


if __name__ == "__main__":
    unittest.main()
