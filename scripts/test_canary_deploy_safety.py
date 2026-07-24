#!/usr/bin/env python3
"""Tests for endurance-gated private canary publication."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_canary_deploy_readiness import validate_readiness
from monitor_endurance import write_summary
from test_endurance_summary import valid_summary


ROOT = Path(__file__).resolve().parents[1]
VERSION = "2026.1.0-hal.9.0-alpha.5"


class CanaryDeploySafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.artifact = self.directory / f"muse-luxe-{VERSION}.ota.bin"
        self.artifact.write_bytes(b"reviewed private canary firmware")
        self.sha256 = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.manifest = self.directory / "manifest-development.json"
        self.summary = self.directory / "endurance.summary.json"
        self.write_manifest()
        summary = valid_summary()
        summary["device"]["project_version"] = VERSION
        write_summary(self.summary, summary)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_manifest(self, **changes: object) -> None:
        manifest = {
            "name": "raspiaudio.voice-assistant",
            "version": VERSION,
            "channel": "development",
            "builds": [{
                "chipFamily": "ESP32",
                "ota": {
                    "md5": hashlib.md5(self.artifact.read_bytes()).hexdigest(),
                    "path": "http://10.10.30.159:8123/local/muse-luxe/channels/development/firmware.ota.bin",
                    "offset": 0,
                    "summary": "fixture",
                },
            }],
        }
        manifest.update(changes)
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def test_exact_candidate_passes_and_returns_closed_destinations(self) -> None:
        result = validate_readiness(
            self.artifact, self.manifest, self.summary, self.sha256
        )
        self.assertEqual(result["version"], VERSION)
        self.assertEqual(
            result["manifest_destination"],
            "muse-luxe/channels/development/manifest.json",
        )

    def test_wrong_or_malformed_reviewed_digest_fails(self) -> None:
        for value in ("0" * 64, "not-a-digest"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_readiness(self.artifact, self.manifest, self.summary, value)

    def test_short_or_wrong_version_endurance_fails(self) -> None:
        summary = valid_summary()
        summary["device"]["project_version"] = VERSION
        summary["observed_duration_seconds"] = 86399
        write_summary(self.summary, summary)
        with self.assertRaises(RuntimeError):
            validate_readiness(self.artifact, self.manifest, self.summary, self.sha256)
        summary = valid_summary()
        summary["device"]["project_version"] = "other-version"
        write_summary(self.summary, summary)
        with self.assertRaises(RuntimeError):
            validate_readiness(self.artifact, self.manifest, self.summary, self.sha256)

    def test_wrong_channel_md5_path_or_filename_fails(self) -> None:
        original = json.loads(self.manifest.read_text(encoding="utf-8"))
        mutations = []
        value = deepcopy(original); value["builds"] = [None]; mutations.append(value)
        value = deepcopy(original); value["name"] = "wrong-project"; mutations.append(value)
        value = deepcopy(original); value["channel"] = "stable"; mutations.append(value)
        value = deepcopy(original); value["builds"][0]["ota"]["md5"] = "0" * 32; mutations.append(value)
        value = deepcopy(original); value["builds"][0]["ota"]["path"] = "https://example.invalid/fw.bin"; mutations.append(value)
        for index, manifest in enumerate(mutations):
            self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                validate_readiness(self.artifact, self.manifest, self.summary, self.sha256)
        self.manifest.write_text(json.dumps(original), encoding="utf-8")
        renamed = self.directory / "firmware.ota.bin"
        self.artifact.rename(renamed)
        with self.assertRaises(RuntimeError):
            validate_readiness(renamed, self.manifest, self.summary, self.sha256)

    def test_deploy_script_validates_before_firmware_and_manifest_last(self) -> None:
        source = (ROOT / "scripts/deploy_local_update.sh").read_text(encoding="utf-8")
        markers = [
            "git status --porcelain",
            "check_canary_deploy_readiness.py",
            '"$FIRMWARE" "$firmware_destination"',
            '"$MANIFEST" "$manifest_destination"',
        ]
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("muse-luxe/manifest.json", source)
        self.assertNotIn("${1:-", source)


if __name__ == "__main__":
    unittest.main()
