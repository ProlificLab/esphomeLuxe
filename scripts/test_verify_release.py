#!/usr/bin/env python3
"""Positive and negative fixtures for release artifact verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts/verify_release.sh"


class VerifyReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_fixture(
        self,
        channel: str,
        version: str,
        *,
        bad_hash: bool = False,
        bad_path: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        artifact = self.directory / f"muse-luxe-{version}.ota.bin"
        artifact.write_bytes(b"release verification fixture")
        digest = hashlib.md5(artifact.read_bytes()).hexdigest()
        if bad_hash:
            digest = "0" * 32
        if channel == "development":
            path = "http://10.10.30.159:8123/local/muse-luxe/channels/development/firmware.ota.bin"
        else:
            path = (
                f"http://10.10.30.159:8123/local/muse-luxe/channels/"
                f"{channel}/firmware-{version}.ota.bin"
            )
        if bad_path:
            path = "https://example.invalid/firmware.ota.bin"
        manifest = self.directory / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "name": "raspiaudio.voice-assistant",
                    "version": version,
                    "channel": channel,
                    "builds": [
                        {
                            "chipFamily": "ESP32",
                            "ota": {"md5": digest, "path": path, "offset": 0},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.run(
            [str(VERIFY), str(manifest), str(artifact)],
            capture_output=True,
            check=False,
            text=True,
        )

    def test_development_passes(self) -> None:
        result = self.run_fixture("development", "2026.1.0-hal.10-alpha.1")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_beta_versioned_path_passes(self) -> None:
        result = self.run_fixture("beta", "2026.1.0-hal.10-beta.1")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stable_passes(self) -> None:
        result = self.run_fixture("stable", "2026.1.0-hal.10")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hash_mismatch_is_rejected(self) -> None:
        result = self.run_fixture(
            "development", "2026.1.0-hal.10-alpha.1", bad_hash=True
        )
        self.assertNotEqual(result.returncode, 0)

    def test_external_path_is_rejected(self) -> None:
        result = self.run_fixture(
            "beta", "2026.1.0-hal.10-beta.1", bad_path=True
        )
        self.assertNotEqual(result.returncode, 0)

    def test_alpha_beta_is_rejected(self) -> None:
        result = self.run_fixture("beta", "2026.1.0-hal.10-alpha.1")
        self.assertNotEqual(result.returncode, 0)

    def test_prerelease_stable_is_rejected(self) -> None:
        result = self.run_fixture("stable", "2026.1.0-hal.10-rc.1")
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_project_version_is_rejected(self) -> None:
        result = self.run_fixture("development", "not-a-project-version")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
