#!/usr/bin/env python3
"""Offline positive and negative tests for the one-shot corrective canary gate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check_corrective_canary_readiness import NEW_VERSION, validate_readiness
from check_build_metadata import ESPHOME_IMAGE
from check_corrective_incident import ERROR_TEXT, derive, validate_record
from seal_corrective_incident import seal


ROOT = Path(__file__).resolve().parents[1]
COMMIT = subprocess.run(
    ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
    check=True, capture_output=True, text=True,
).stdout.strip()
EPOCH = int(subprocess.run(
    ["git", "-C", str(ROOT), "show", "-s", "--format=%ct", COMMIT],
    check=True, capture_output=True, text=True,
).stdout.strip())


class CorrectiveCanaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.old = self.root / "old.ota.bin"
        self.old.write_bytes(b"exact old firmware")
        self.old_sha = hashlib.sha256(self.old.read_bytes()).hexdigest()
        self.raw = self.root / "incident.jsonl"
        self.write_raw()
        self.record = self.root / "incident.json"
        seal(self.record, self.raw, self.old, self.old_sha)
        self.new = self.root / f"muse-luxe-{NEW_VERSION}.ota.bin"
        self.new.write_bytes(b"exact corrective firmware")
        self.new_sha = hashlib.sha256(self.new.read_bytes()).hexdigest()
        self.manifest = self.root / "manifest-development.json"
        self.write_manifest()
        self.metadata = self.root / "build-metadata.json"
        self.write_metadata()
        self.ci = self.root / "ci.json"
        self.ci.write_text(json.dumps({
            "conclusion": "success", "databaseId": 123, "event": "pull_request",
            "headSha": COMMIT, "jobs": [{"name": "compile", "databaseId": 456,
            "status": "completed", "conclusion": "success"}],
            "name": "Firmware source validation", "status": "completed",
            "url": "https://github.com/ProlificLab/esphomeLuxe/actions/runs/123",
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_raw(self, *, errors: int = 1, recoveries: int = 1,
                  duration: int = 86400) -> None:
        started = datetime.now(timezone.utc) - timedelta(days=1, minutes=1)
        rows = []
        for index in range(1441):
            triggered = index >= 800
            rows.append({
                "timestamp": (started + timedelta(seconds=index * duration / 1440)).isoformat(),
                "elapsed_seconds": index * duration / 1440,
                "uptime": index * duration / 1440 + 1,
                "voice_errors": errors if triggered else 0,
                "voice_recoveries": recoveries if triggered else 0,
                "voice_timeouts": 0,
                "last_voice_error": ERROR_TEXT if triggered else "",
                "voice_state": "offline" if triggered else "waiting",
                "voice_health": "offline" if triggered else "healthy",
            })
        self.raw.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def write_manifest(self, version: str = NEW_VERSION) -> None:
        self.manifest.write_text(json.dumps({
            "name": "raspiaudio.voice-assistant", "version": version,
            "channel": "development", "builds": [{"chipFamily": "ESP32", "ota": {
                "md5": hashlib.md5(self.new.read_bytes()).hexdigest(),
                "path": "http://10.10.30.159:8123/local/muse-luxe/channels/development/firmware.ota.bin",
                "offset": 0, "summary": "fixture",
            }}],
        }), encoding="utf-8")

    def write_metadata(self, **changes: object) -> None:
        metadata = {
            "version": NEW_VERSION, "channel": "development",
            "source_commit": COMMIT, "source_date_epoch": EPOCH,
            "config": "luxe_microWW.yaml", "artifact": self.new.name,
            "size_bytes": self.new.stat().st_size,
            "md5": hashlib.md5(self.new.read_bytes()).hexdigest(),
            "sha256": self.new_sha, "esphome_image": ESPHOME_IMAGE,
            "esp_idf": "5.4.2",
        }
        metadata.update(changes)
        self.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    def readiness(self) -> dict:
        return validate_readiness(
            self.new, self.manifest, self.metadata, self.record, self.raw,
            self.old, self.ci, self.new_sha, self.old_sha, COMMIT,
        )

    def test_exact_incident_and_candidate_pass(self) -> None:
        record = validate_record(self.record, self.raw, self.old, self.old_sha)
        self.assertFalse(record["passed"])
        self.assertEqual(self.readiness()["new_version"], NEW_VERSION)

    def test_short_or_different_incident_fails(self) -> None:
        for changes in ({"duration": 86399}, {"errors": 2}, {"recoveries": 0}):
            with self.subTest(changes=changes):
                self.write_raw(**changes)
                with self.assertRaises(RuntimeError):
                    derive(self.raw, self.old, self.old_sha)

    def test_unknown_final_state_fails(self) -> None:
        rows = [json.loads(line) for line in self.raw.read_text(encoding="utf-8").splitlines()]
        rows[-1]["voice_state"] = "error"
        self.raw.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            derive(self.raw, self.old, self.old_sha)

    def test_tampered_raw_record_or_old_firmware_fails(self) -> None:
        changed = json.loads(self.record.read_text(encoding="utf-8"))
        changed["sample_count"] += 1
        self.record.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_record(self.record, self.raw, self.old, self.old_sha)
        self.record.unlink()
        seal(self.record, self.raw, self.old, self.old_sha)
        self.old.write_bytes(b"changed")
        with self.assertRaises(RuntimeError):
            validate_record(self.record, self.raw, self.old, self.old_sha)

    def test_wrong_candidate_version_digest_or_ci_fails(self) -> None:
        self.write_manifest("2025.3.1-hal.9.0-alpha.5")
        with self.assertRaises(RuntimeError):
            self.readiness()
        self.write_manifest()
        for new_sha, commit in (("0" * 64, COMMIT), (self.new_sha, "b" * 40)):
            with self.subTest(new_sha=new_sha, commit=commit), self.assertRaises(RuntimeError):
                validate_readiness(
                    self.new, self.manifest, self.metadata, self.record, self.raw,
                    self.old, self.ci, new_sha, self.old_sha, commit,
                )

    def test_wrong_build_metadata_fails(self) -> None:
        for changes in (
            {"source_commit": "0" * 40},
            {"source_date_epoch": EPOCH + 1},
            {"sha256": "0" * 64},
        ):
            self.write_metadata(**changes)
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                self.readiness()

    def test_installer_is_closed_and_orders_all_gates_before_upload(self) -> None:
        source = (ROOT / "scripts/install_corrective_canary_ota.sh").read_text(encoding="utf-8")
        markers = [
            "git -C \"$ROOT\" status --porcelain",
            "check_corrective_canary_readiness.py",
            "CORRECTIVE_INSTALL_CONFIRM",
            "upload_exact_ota.py",
            "verify_canary_boot.py",
        ]
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("install_canary_ota.sh", source)
        self.assertNotIn("rollback_hal6_ota.sh", source)
        self.assertNotIn("esphome upload", source)


if __name__ == "__main__":
    unittest.main()
