#!/usr/bin/env python3
"""Offline fixtures for immutable hal.6 credential compatibility."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import yaml

from check_hal6_credential_compatibility import validate


VALUES = {
    "api_encryption_key": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    "ota_password": "replace-with-a-long-random-password",
    "fallback_ap_password": "replace-with-random",
    "unrelated": "preserved",
}


class Hal6CredentialCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.active = self.root / "active.yaml"
        self.reference = self.root / "reference.yaml"
        self.write(self.active, VALUES, 0o600)
        self.write(self.reference, VALUES, 0o644)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, path: Path, value: dict[str, str], mode: int) -> None:
        path.write_text(yaml.safe_dump(value), encoding="utf-8"); path.chmod(mode)

    def test_exact_domain_passes_without_values(self) -> None:
        result = validate(self.active, self.reference)
        self.assertEqual(result["credential_keys_matched"], 3)
        self.assertTrue(result["ota_safe"])
        self.assertFalse(any(value in str(result) for value in VALUES.values()))

    def test_each_rotated_value_refuses_ota_rollback(self) -> None:
        for key in ("api_encryption_key", "ota_password", "fallback_ap_password"):
            changed = dict(VALUES); changed[key] = f"rotated-{key}-private-value"
            self.write(self.active, changed, 0o600)
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate(self.active, self.reference)

    def test_insecure_or_symlink_active_file_fails(self) -> None:
        self.active.chmod(0o644)
        with self.assertRaises(RuntimeError): validate(self.active, self.reference)
        self.active.unlink(); self.active.symlink_to(self.reference)
        with self.assertRaises(RuntimeError): validate(self.active, self.reference)

    def test_missing_or_malformed_inputs_fail(self) -> None:
        changed = dict(VALUES); changed.pop("ota_password")
        self.write(self.active, changed, 0o600)
        with self.assertRaises(RuntimeError): validate(self.active, self.reference)
        self.reference.write_text("[]", encoding="utf-8")
        with self.assertRaises(RuntimeError): validate(self.active, self.reference)


if __name__ == "__main__":
    unittest.main()
