#!/usr/bin/env python3
"""Offline tests for post-verification credential activation and orchestration."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import yaml

from activate_secret_rotation import activate
from monitor_endurance import write_summary
from prepare_secret_rotation import prepare
from test_endurance_summary import VERSION, valid_summary


ROOT = Path(__file__).resolve().parents[1]
CURRENT = {
    "api_encryption_key": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    "ota_password": "replace-with-a-long-random-password",
    "fallback_ap_password": "replace-with-random",
}


class RotationActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.active = self.root / "active.yaml"
        self.active.write_text(yaml.safe_dump(CURRENT), encoding="utf-8")
        self.active.chmod(0o600)
        self.endurance = self.root / "endurance-summary.json"
        write_summary(self.endurance, valid_summary())
        self.bundle = self.root / "rotation"
        prepare(self.active, self.bundle, self.endurance, VERSION)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_activation_replaces_active_then_retires_transition(self) -> None:
        expected = (self.bundle / "secrets.yaml").read_text(encoding="utf-8")
        result = activate(self.bundle, self.active)
        self.assertEqual(self.active.read_text(encoding="utf-8"), expected)
        self.assertFalse((self.bundle / "transition-ota.yaml").exists())
        self.assertEqual(result["status"], "activated_verified")
        manifest = json.loads((self.bundle / "rotation-manifest.json").read_text())
        self.assertTrue(manifest["transition_retired"])
        self.assertEqual(activate(self.bundle, self.active), result)

    def test_unrelated_active_secret_refuses_without_changes(self) -> None:
        self.active.write_text("ota_password: unrelated-private-value\n", encoding="utf-8")
        before = self.active.read_bytes()
        with self.assertRaises(RuntimeError):
            activate(self.bundle, self.active)
        self.assertEqual(self.active.read_bytes(), before)
        self.assertTrue((self.bundle / "transition-ota.yaml").exists())

        new = yaml.safe_load((self.bundle / "secrets.yaml").read_text())
        new["api_encryption_key"] = CURRENT["api_encryption_key"]
        self.active.write_text(yaml.safe_dump(new), encoding="utf-8")
        self.active.chmod(0o600)
        with self.assertRaises(RuntimeError):
            activate(self.bundle, self.active)

    def test_orchestrator_orders_closed_checks_upload_verify_and_activation(self) -> None:
        wrapper = (ROOT / "scripts/install_rotated_canary_ota.sh").read_text()
        base = (ROOT / "scripts/install_canary_ota.sh").read_text()
        markers = [
            "check_secret_rotation_bundle.py",
            "audit_tracked_secrets.py",
            "check_canary_deploy_readiness.py",
            "check_rotated_candidate_binding.py",
            "ROTATION_INSTALL_CONFIRM",
            "install_canary_ota.sh",
            "activate_secret_rotation.py",
        ]
        positions = [wrapper.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('OTA_SECRETS="$ROTATION_DIR/transition-ota.yaml"', wrapper)
        self.assertIn('VERIFY_SECRETS="$ROTATION_DIR/secrets.yaml"', wrapper)
        self.assertIn('SOURCE_EVIDENCE="${7:?$usage}"', wrapper)
        self.assertEqual(wrapper.count('"$ENDURANCE_SUMMARY" --expected-version'), 2)
        self.assertEqual(wrapper.count("check_rotated_candidate_binding.py"), 2)
        self.assertLess(
            wrapper.rindex("check_rotated_candidate_binding.py"),
            wrapper.index("install_canary_ota.sh"),
        )
        self.assertLess(base.index("upload_exact_ota.py"), base.index("verify_canary_boot.py"))
        self.assertIn('--secrets "$VERIFY_SECRETS"', base)


if __name__ == "__main__":
    unittest.main()
