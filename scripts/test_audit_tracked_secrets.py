#!/usr/bin/env python3
"""Tests for value-redacting tracked-secret audit."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from audit_tracked_secrets import audit, write_atomic


class TrackedSecretsAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.secrets = self.root / "private.yaml"
        self.secrets.write_text(
            'api_encryption_key: "REAL-ENCRYPTION-VALUE-123"\n'
            'ota_password: "REAL-OTA-PASSWORD-456"\n'
            'update_manifest_url: "http://not-sensitive"\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def track(self, name: str, content: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", name], check=True)

    def test_clean_repository_counts_private_keys_without_values(self) -> None:
        self.track("config.yaml", "password: !secret ota_password\n")
        report = audit(self.root, self.secrets)
        self.assertTrue(report["passed"])
        self.assertEqual(report["private_secret_keys_checked"], 2)
        rendered = json.dumps(report)
        self.assertNotIn("REAL-ENCRYPTION", rendered)
        self.assertNotIn("REAL-OTA", rendered)

    def test_exact_private_value_reports_only_key_and_path(self) -> None:
        self.track("leak.txt", "REAL-OTA-PASSWORD-456\n")
        report = audit(self.root, self.secrets)
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["findings"]["exact_secret_matches"],
            [{"key": "ota_password", "path": "leak.txt"}],
        )
        self.assertNotIn("REAL-OTA-PASSWORD-456", json.dumps(report))

    def test_token_private_key_and_prohibited_file_fail(self) -> None:
        self.track("token.txt", "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n")
        self.track("identity.pem", "-----BEGIN " + "PRIVATE KEY-----\n")
        report = audit(self.root, self.secrets)
        self.assertFalse(report["passed"])
        self.assertEqual(len(report["findings"]["suspicious_pattern_matches"]), 2)
        self.assertEqual(report["findings"]["prohibited_tracked_files"], ["identity.pem"])

    def test_placeholder_private_values_are_not_compared(self) -> None:
        self.secrets.write_text(
            'ota_password: "replace-with-a-long-password"\n'
            'api_encryption_key: "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="\n',
            encoding="utf-8",
        )
        self.track("example.txt", "replace-with-a-long-password\n")
        report = audit(self.root, self.secrets)
        self.assertTrue(report["passed"])
        self.assertEqual(report["private_secret_keys_checked"], 0)

    def test_atomic_report_contains_no_secret(self) -> None:
        self.track("config.yaml", "safe: true\n")
        report = audit(self.root, self.secrets)
        output = self.root / "audit.json"
        write_atomic(output, report)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
        self.assertFalse(list(self.root.glob(".audit.json.*.tmp")))


if __name__ == "__main__":
    unittest.main()
