#!/usr/bin/env python3
"""Offline tests for exact canary installation and rollback controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_rollback_artifact import validate_rollback
from verify_canary_boot import validate_observation


ROOT = Path(__file__).resolve().parents[1]


class CanaryInstallSafetyTests(unittest.TestCase):
    def test_boot_requires_exact_version_and_healthy_idle_state(self) -> None:
        valid = {"voice_state": "waiting", "voice_health": "healthy", "last_voice_error": ""}
        validate_observation("v1", "v1", valid)
        mutations = [
            ("v2", valid),
            ("v1", {**valid, "voice_state": "answering"}),
            ("v1", {**valid, "voice_health": "degraded"}),
            ("v1", {**valid, "last_voice_error": "timeout"}),
        ]
        for version, states in mutations:
            with self.subTest(version=version, states=states), self.assertRaises(RuntimeError):
                validate_observation(version, "v1", states)

    def test_hal6_rollback_binds_sha_and_manifest_md5(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "hal6.ota.bin"
            artifact.write_bytes(b"retained hal6")
            sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "name": "raspiaudio.voice-assistant",
                "version": "2025.3.1-hal.6",
                "builds": [{"ota": {
                    "md5": hashlib.md5(artifact.read_bytes()).hexdigest(),
                    "offset": 0,
                }}],
            }), encoding="utf-8")
            self.assertEqual(validate_rollback(artifact, manifest, sha256), "2025.3.1-hal.6")
            with self.assertRaises(RuntimeError):
                validate_rollback(artifact, manifest, "0" * 64)
            changed = json.loads(manifest.read_text(encoding="utf-8"))
            changed["builds"][0]["ota"]["md5"] = "0" * 32
            manifest.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                validate_rollback(artifact, manifest, sha256)
            manifest.write_text("[]", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                validate_rollback(artifact, manifest, sha256)

    def test_install_orders_preflight_confirmation_upload_then_boot_check(self) -> None:
        source = (ROOT / "scripts/install_canary_ota.sh").read_text(encoding="utf-8")
        markers = [
            "git -C \"$ROOT\" status --porcelain",
            "check_canary_deploy_readiness.py",
            "CANARY_INSTALL_CONFIRM",
            "upload_exact_ota.py",
            "verify_canary_boot.py",
        ]
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("esphome upload", source)
        self.assertNotIn("cp \"$FIRMWARE\"", source)

    def test_rollback_is_separate_and_requires_exact_confirmation(self) -> None:
        install = (ROOT / "scripts/install_canary_ota.sh").read_text(encoding="utf-8")
        rollback = (ROOT / "scripts/rollback_hal6_ota.sh").read_text(encoding="utf-8")
        self.assertNotIn("rollback_hal6_ota.sh", install)
        self.assertIn("ROLLBACK $version $EXPECTED_SHA256", rollback)
        self.assertIn("check_rollback_artifact.py", rollback)
        self.assertIn("check_hal6_credential_compatibility.py", rollback)
        self.assertIn("HAL6_REFERENCE_SECRETS", rollback)
        self.assertNotIn('"$ROOT/secrets.example.yaml"', rollback)
        self.assertLess(
            rollback.index("check_hal6_credential_compatibility.py"),
            rollback.index("ROLLBACK $version $EXPECTED_SHA256"),
        )
        self.assertIn("verify_canary_boot.py", rollback)


if __name__ == "__main__":
    unittest.main()
