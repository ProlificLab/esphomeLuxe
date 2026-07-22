#!/usr/bin/env python3
"""Offline tests for the immutable OTA upload snapshot."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from upload_exact_ota import verified_snapshot


class ExactOtaSnapshotTests(unittest.TestCase):
    def test_snapshot_matches_reviewed_bytes_and_is_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "candidate.ota.bin"
            reviewed = b"reviewed firmware bytes"
            artifact.write_bytes(reviewed)
            expected = hashlib.sha256(reviewed).hexdigest()
            with verified_snapshot(artifact, expected) as snapshot:
                artifact.write_bytes(b"mutated host artifact")
                self.assertEqual(snapshot.read_bytes(), reviewed)
                self.assertNotEqual(snapshot.resolve(), artifact.resolve())

    def test_wrong_digest_empty_symlink_and_invalid_digest_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "candidate.ota.bin"
            artifact.write_bytes(b"firmware")
            for expected in ("0" * 64, "not-a-digest"):
                with self.subTest(expected=expected), self.assertRaises(RuntimeError):
                    with verified_snapshot(artifact, expected):
                        pass
            empty = root / "empty.bin"
            empty.touch()
            with self.assertRaises(RuntimeError):
                with verified_snapshot(empty, hashlib.sha256(b"").hexdigest()):
                    pass
            link = root / "link.bin"
            link.symlink_to(artifact)
            with self.assertRaises(RuntimeError):
                with verified_snapshot(link, hashlib.sha256(b"firmware").hexdigest()):
                    pass


if __name__ == "__main__":
    unittest.main()
