#!/usr/bin/env python3
"""Offline safety tests for source qualification collection."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from check_private_log_disclosure import check


ROOT = Path(__file__).resolve().parents[1]


class SourceQualificationCollectionTests(unittest.TestCase):
    def test_log_check_passes_without_disclosing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secrets = root / "secrets.yaml"
            values = ("REAL-API-ENCRYPTION-123", "REAL-OTA-PASSWORD-456", "REAL-AP-PASSWORD-789")
            secrets.write_text(
                f'api_encryption_key: "{values[0]}"\nota_password: "{values[1]}"\n'
                f'fallback_ap_password: "{values[2]}"\n', encoding="utf-8")
            log = root / "build.log"; log.write_text("safe build output\n", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output): report = check(secrets, [log])
            self.assertTrue(report["passed"])
            self.assertFalse(any(value in str(report) + output.getvalue() for value in values))

    def test_log_check_reports_only_key_and_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); secrets = root / "private.yaml"; log = root / "ci.log"
            secrets.write_text("api_encryption_key: REAL-PRIVATE-API-123\nota_password: REAL-PRIVATE-OTA-456\n"
                               "fallback_ap_password: REAL-PRIVATE-AP-789\n", encoding="utf-8")
            log.write_text("leak REAL-PRIVATE-OTA-456", encoding="utf-8")
            report = check(secrets, [log])
            self.assertFalse(report["passed"])
            self.assertEqual(report["disclosures"], [{"key": "ota_password", "path": "ci.log"}])
            self.assertNotIn("REAL-PRIVATE-OTA-456", str(report))
            with self.assertRaises(RuntimeError):
                check(secrets, [log, log])

    def test_collector_closes_order_and_runs_two_pinned_clean_builds(self) -> None:
        source = (ROOT / "scripts/collect_source_qualification.sh").read_text(encoding="utf-8")
        markers = ["config_version=", "status --porcelain", "audit_tracked_secrets.py",
                   "check_source_ci_preflight.py", "secrets_sha=", "first_sha=", "second_sha=",
                   '[[ "$first_sha" != "$second_sha" ]]', "check_firmware_size.sh",
                   "check_private_log_disclosure.py", "seal_source_qualification_evidence.py"]
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count('"$IMAGE" clean "$CONFIG"'), 1)
        self.assertEqual(source.count('"$IMAGE" compile "$CONFIG"'), 1)
        self.assertIn("build_once", source)
        self.assertEqual(source.count('$SECRETS_ABS:/config/secrets.yaml:ro'), 2)
        self.assertIn("SECRETS SHA256=%s", source)
        self.assertIn("Private secrets changed before a source build", source)
        self.assertIn("Private secrets changed during a source build", source)
        self.assertIn('--private-secrets "$SECRETS_ABS"', source)
        self.assertNotIn("upload_exact_ota", source)
        self.assertNotIn("verify_canary_boot", source)


if __name__ == "__main__":
    unittest.main()
