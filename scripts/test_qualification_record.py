#!/usr/bin/env python3
"""Unit and negative tests for release qualification records."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import check_qualification_record as checker


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_qualification_record.py"
COMMIT = "a" * 40


def gate() -> dict[str, object]:
    return {"passed": True, "evidence": "CI run 123456 and reviewed log"}


class QualificationRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.artifact = self.directory / "muse-luxe-2026.1.0-hal.10.ota.bin"
        self.artifact.write_bytes(b"qualified firmware fixture")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def record(self, channel: str, version: str) -> dict[str, object]:
        required = checker.STABLE_GATES if channel == "stable" else checker.BETA_GATES
        return {
            "schema_version": 1,
            "channel": channel,
            "version": version,
            "source_commit": COMMIT,
            "firmware_sha256": self.digest,
            "reviewer": "Household release reviewer",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "canary_device": "muse-luxe-canary-bureau",
            "compatibility": {
                "hardware": "Raspiaudio Muse Luxe ESP32",
                "home_assistant": "2026.7.2",
                "esphome": "2025.10.5",
                "esp_idf": "5.4.2",
            },
            "feature_scope": ["voice satellite", "local recovery"],
            "open_gates": [] if channel == "stable" else ["stable gates remain"],
            "gates": {name: gate() for name in required},
        }

    def run_check(
        self,
        record: dict[str, object],
        channel: str,
        version: str,
    ) -> subprocess.CompletedProcess[str]:
        record_path = self.directory / "qualification.json"
        manifest_path = self.directory / "manifest.json"
        record_path.write_text(json.dumps(record), encoding="utf-8")
        manifest_path.write_text(
            json.dumps({"version": version, "channel": channel}),
            encoding="utf-8",
        )
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--record",
                str(record_path),
                "--manifest",
                str(manifest_path),
                "--artifact",
                str(self.artifact),
                "--channel",
                channel,
                "--source-commit",
                COMMIT,
            ],
            capture_output=True,
            check=False,
            text=True,
        )

    def test_beta_record_passes(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        result = self.run_check(self.record("beta", version), "beta", version)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stable_record_passes(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(self.record("stable", version), "stable", version)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["gates"].pop("tts_cycles_100")
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_false_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["gates"]["canary_ota"]["passed"] = False
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_hash_mismatch_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["firmware_sha256"] = "0" * 64
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_commit_mismatch_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["source_commit"] = "b" * 40
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_stable_prerelease_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-rc.1"
        record = self.record("stable", version)
        self.assertNotEqual(self.run_check(record, "stable", version).returncode, 0)

    def test_stable_open_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        record["open_gates"] = ["physical gate remains"]
        self.assertNotEqual(self.run_check(record, "stable", version).returncode, 0)


if __name__ == "__main__":
    unittest.main()
