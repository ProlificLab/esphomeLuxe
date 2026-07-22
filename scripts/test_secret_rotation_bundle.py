#!/usr/bin/env python3
"""Negative and positive fixtures for private rotation bundles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from check_secret_rotation_bundle import validate_bundle
from monitor_endurance import write_summary
from prepare_secret_rotation import prepare
from test_endurance_summary import VERSION, valid_summary


CURRENT = {
    "api_encryption_key": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    "ota_password": "replace-with-a-long-random-password",
    "fallback_ap_password": "replace-with-random",
    "wifi_ssid": "preserved-network",
}


class SecretRotationBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        current = self.root / "current.yaml"
        current.write_text(yaml.safe_dump(CURRENT), encoding="utf-8")
        current.chmod(0o600)
        self.endurance = self.root / "endurance-summary.json"
        write_summary(self.endurance, valid_summary())
        self.bundle = self.root / "rotation"
        prepare(current, self.bundle, self.endurance, VERSION)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def rewrite_manifest(self, value: dict[str, object]) -> None:
        path = self.bundle / "rotation-manifest.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        path.chmod(0o600)

    def test_exact_private_bundle_passes_without_values(self) -> None:
        result = validate_bundle(self.bundle, self.endurance, VERSION)
        self.assertTrue(result["passed"])
        self.assertEqual(result["rotated_key_count"], 3)
        self.assertTrue(result["endurance_summary_bound"])
        contents = (self.bundle / "secrets.yaml").read_text(encoding="utf-8")
        for value in yaml.safe_load(contents).values():
            self.assertNotIn(str(value), str(result))

    def test_permissions_and_symlinks_fail(self) -> None:
        (self.bundle / "secrets.yaml").chmod(0o644)
        with self.assertRaises(RuntimeError):
            validate_bundle(self.bundle)
        (self.bundle / "secrets.yaml").chmod(0o600)
        target = self.bundle / "transition-ota.yaml"
        target.unlink()
        target.symlink_to(self.bundle / "secrets.yaml")
        with self.assertRaises(RuntimeError):
            validate_bundle(self.bundle)

    def test_manifest_schema_status_and_age_fail(self) -> None:
        manifest = json.loads(
            (self.bundle / "rotation-manifest.json").read_text(encoding="utf-8")
        )
        for field, value in (
            ("status", "completed"),
            ("network_actions_performed", 1),
            ("schema_version", True),
            ("network_actions_performed", False),
            ("files", {"new_secrets": "../escape", "transition_ota": "transition-ota.yaml"}),
            ("generated_at", (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()),
            ("endurance", {"passed": True}),
        ):
            changed = dict(manifest)
            changed[field] = value
            self.rewrite_manifest(changed)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate_bundle(self.bundle)

    def test_endurance_digest_version_and_content_are_bound(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_bundle(
                self.bundle, self.endurance, "2026.1.0-hal.10-wrong"
            )

        changed = valid_summary()
        changed["sample_count"] += 1
        write_summary(self.endurance, changed)
        with self.assertRaises(RuntimeError):
            validate_bundle(self.bundle, self.endurance, VERSION)

    def test_fixture_weak_duplicate_and_zero_api_values_fail(self) -> None:
        path = self.bundle / "secrets.yaml"
        original = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutations = (
            ("ota_password", "replace-with-a-long-random-password"),
            ("fallback_ap_password", original["ota_password"]),
            ("api_encryption_key", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
            ("api_encryption_key", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="),
        )
        for key, value in mutations:
            changed = dict(original)
            changed[key] = value
            path.write_text(yaml.safe_dump(changed), encoding="utf-8")
            path.chmod(0o600)
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_bundle(self.bundle)

    def test_transition_is_old_ota_only_and_must_differ(self) -> None:
        path = self.bundle / "transition-ota.yaml"
        rotated = yaml.safe_load((self.bundle / "secrets.yaml").read_text(encoding="utf-8"))
        for value in (
            {"ota_password": rotated["ota_password"]},
            {"ota_password": CURRENT["ota_password"], "api_encryption_key": "forbidden"},
        ):
            path.write_text(yaml.safe_dump(value), encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaises(RuntimeError):
                validate_bundle(self.bundle)


if __name__ == "__main__":
    unittest.main()
