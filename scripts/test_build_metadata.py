#!/usr/bin/env python3
"""Positive and negative fixtures for deterministic artifact metadata."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check_build_metadata import ESPHOME_IMAGE, validate_metadata


ROOT = Path(__file__).resolve().parents[1]
COMMIT = subprocess.run(
    ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
    check=True, capture_output=True, text=True,
).stdout.strip()
EPOCH = int(subprocess.run(
    ["git", "-C", str(ROOT), "show", "-s", "--format=%ct", COMMIT],
    check=True, capture_output=True, text=True,
).stdout.strip())
VERSION = "2025.3.1-hal.9.0-alpha.6"


class BuildMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifact = self.root / f"muse-luxe-{VERSION}.ota.bin"
        self.artifact.write_bytes(b"deterministic candidate")
        self.path = self.root / "build-metadata.json"
        self.metadata = {
            "version": VERSION,
            "channel": "development",
            "source_commit": COMMIT,
            "source_date_epoch": EPOCH,
            "config": "luxe_microWW.yaml",
            "artifact": self.artifact.name,
            "size_bytes": self.artifact.stat().st_size,
            "md5": hashlib.md5(self.artifact.read_bytes()).hexdigest(),
            "sha256": hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
            "esphome_image": ESPHOME_IMAGE,
            "esp_idf": "5.4.2",
        }
        self.write()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, metadata: dict | None = None) -> None:
        self.path.write_text(json.dumps(metadata or self.metadata), encoding="utf-8")

    def test_exact_metadata_passes(self) -> None:
        result = validate_metadata(self.path, self.artifact, COMMIT, ROOT)
        self.assertEqual(result["source_date_epoch"], EPOCH)

    def test_every_identity_field_is_closed(self) -> None:
        mutations = {
            "version": "free-form",
            "channel": "stable",
            "source_commit": "0" * 40,
            "source_date_epoch": EPOCH + 1,
            "config": "luxe_microWW_nabu.yaml",
            "artifact": "firmware.ota.bin",
            "size_bytes": 1,
            "md5": "0" * 32,
            "sha256": "0" * 64,
            "esphome_image": "esphome/esphome:latest",
            "esp_idf": "latest",
        }
        for field, value in mutations.items():
            changed = deepcopy(self.metadata); changed[field] = value
            self.write(changed)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate_metadata(self.path, self.artifact, COMMIT, ROOT)

    def test_wrong_commit_changed_artifact_or_extra_key_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_metadata(self.path, self.artifact, "0" * 40, ROOT)
        self.artifact.write_bytes(b"changed")
        with self.assertRaises(RuntimeError):
            validate_metadata(self.path, self.artifact, COMMIT, ROOT)
        self.artifact.write_bytes(b"deterministic candidate")
        changed = deepcopy(self.metadata); changed["extra"] = True; self.write(changed)
        with self.assertRaises(RuntimeError):
            validate_metadata(self.path, self.artifact, COMMIT, ROOT)


if __name__ == "__main__":
    unittest.main()
