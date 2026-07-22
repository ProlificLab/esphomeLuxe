#!/usr/bin/env python3
"""Offline fixtures for exact rotated-credential build binding."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from check_rotated_candidate_binding import validate_binding
from prepare_secret_rotation import prepare
from test_source_qualification_evidence import (
    SIZE_BYTES,
    SOURCE_COMMIT,
    valid_evidence,
    write_log_fixtures,
)


VERSION = "2026.1.0-hal.10-beta.1"
CURRENT = {
    "api_encryption_key": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    "ota_password": "replace-with-a-long-random-password",
    "fallback_ap_password": "replace-with-random",
}


class RotatedCandidateBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.current = self.root / "current.yaml"
        self.current.write_text(
            "\n".join(f'{key}: "{value}"' for key, value in CURRENT.items()) + "\n",
            encoding="utf-8",
        )
        self.current.chmod(0o600)
        self.bundle = self.root / "rotation"
        prepare(self.current, self.bundle)
        self.artifact = self.root / "candidate.ota.bin"
        self.artifact.write_bytes(b"x" * SIZE_BYTES)
        self.evidence_path = self.root / "source.json"
        self.write_evidence()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_evidence(self) -> None:
        evidence = valid_evidence()
        evidence["candidate"]["project_version"] = VERSION
        evidence["candidate"]["source_commit"] = SOURCE_COMMIT
        firmware_sha = hashlib.sha256(
            self.artifact.read_bytes()
        ).hexdigest()
        evidence["candidate"]["firmware_sha256"] = firmware_sha
        evidence["build"]["first_sha256"] = firmware_sha
        evidence["build"]["second_sha256"] = firmware_sha
        evidence["ci"]["head_sha"] = SOURCE_COMMIT
        evidence["credentials"]["file_sha256"] = hashlib.sha256(
            (self.bundle / "secrets.yaml").read_bytes()
        ).hexdigest()
        evidence["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        write_log_fixtures(self.root, evidence)
        self.evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    def test_exact_rotated_candidate_binding_passes_without_values(self) -> None:
        result = validate_binding(
            self.artifact, self.evidence_path, self.bundle, VERSION
        )
        self.assertTrue(result["credentials_bound"])
        self.assertEqual(result["build_count"], 2)
        private = yaml.safe_load((self.bundle / "secrets.yaml").read_text(encoding="utf-8"))
        self.assertFalse(any(value in str(result) for value in private.values()))

    def test_wrong_artifact_or_version_fails(self) -> None:
        self.artifact.write_bytes(b"y" * SIZE_BYTES)
        with self.assertRaises(RuntimeError):
            validate_binding(self.artifact, self.evidence_path, self.bundle, VERSION)
        self.artifact.write_bytes(b"x" * SIZE_BYTES)
        with self.assertRaises(RuntimeError):
            validate_binding(
                self.artifact, self.evidence_path, self.bundle, VERSION + ".2"
            )

    def test_different_rotation_bundle_fails_before_install(self) -> None:
        other = self.root / "other"
        prepare(self.current, other)
        with self.assertRaises(RuntimeError):
            validate_binding(self.artifact, self.evidence_path, other, VERSION)

    def test_tampered_evidence_or_build_log_fails(self) -> None:
        evidence = json.loads(self.evidence_path.read_text())
        evidence["credentials"]["file_sha256"] = "0" * 64
        self.evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_binding(self.artifact, self.evidence_path, self.bundle, VERSION)
        self.write_evidence()
        (self.root / "build_first.log").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_binding(self.artifact, self.evidence_path, self.bundle, VERSION)


if __name__ == "__main__":
    unittest.main()
