#!/usr/bin/env python3
"""Tests for atomic core-canary evidence sealing."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seal_canary_core_evidence import LOG_FILES, seal_record
from test_canary_core_evidence import (
    DEVICE,
    FIRMWARE_SHA,
    ROLLBACK_MD5,
    SOURCE_COMMIT,
    VERSION,
    valid_evidence,
)


class SealCanaryCoreEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.logs = self.directory / "logs"
        self.logs.mkdir()
        for name, filename in LOG_FILES.items():
            (self.logs / filename).write_text(f"reviewed {name}\n", encoding="utf-8")
        self.draft = self.directory / "draft.json"
        draft = valid_evidence()
        draft["passed"] = False
        draft["tests"]["rollback_artifact"]["stored_offline"] = True
        self.draft.write_text(json.dumps(draft), encoding="utf-8")
        self.output = self.directory / "canary-core.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def seal(self, **changes: object) -> dict:
        values = {
            "version": VERSION,
            "firmware_sha256": FIRMWARE_SHA,
            "source_commit": SOURCE_COMMIT,
            "device": DEVICE,
            "hardware": "Raspiaudio Muse Luxe ESP32",
            "observer": "Household release reviewer",
            "started_at": valid_evidence()["started_at"],
            "finished_at": valid_evidence()["finished_at"],
            "rollback_sha256": "c" * 64,
            "rollback_md5": ROLLBACK_MD5,
            "rollback_size": 1900000,
        }
        values.update(changes)
        return seal_record(self.draft, self.output, self.logs, **values)

    def test_seals_identity_rollback_and_seven_distinct_logs(self) -> None:
        self.seal()
        sealed = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertTrue(sealed["passed"])
        self.assertEqual(sealed["candidate"]["firmware_sha256"], FIRMWARE_SHA)
        self.assertEqual(sealed["tests"]["rollback_artifact"]["md5"], ROLLBACK_MD5)
        self.assertEqual(len(set(sealed["logs"].values())), 7)
        self.assertFalse(list(self.directory.glob(".canary-core.json.*.tmp")))

    def test_refuses_overwrite(self) -> None:
        self.output.write_text("reviewed prior record\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.seal()
        self.assertEqual(
            self.output.read_text(encoding="utf-8"), "reviewed prior record\n"
        )

    def test_concurrent_output_wins_without_clobber_or_temporary_file(self) -> None:
        def concurrent_create(_source: object, destination: object) -> None:
            Path(destination).write_text("concurrent reviewed record\n", encoding="utf-8")
            raise FileExistsError

        with patch("seal_canary_core_evidence.os.link", side_effect=concurrent_create):
            with self.assertRaises(RuntimeError):
                self.seal()
        self.assertEqual(
            self.output.read_text(encoding="utf-8"), "concurrent reviewed record\n"
        )
        self.assertFalse(list(self.directory.glob(".canary-core.json.*.tmp")))

    def test_missing_or_external_log_leaves_no_output(self) -> None:
        (self.logs / LOG_FILES["tts_cycles"]).unlink()
        with self.assertRaises(RuntimeError):
            self.seal()
        self.assertFalse(self.output.exists())
        outside = self.directory.parent / f"{self.directory.name}-outside-canary-logs"
        outside.mkdir()
        try:
            for name, filename in LOG_FILES.items():
                (outside / filename).write_text(f"outside {name}\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                seal_record(
                    self.draft,
                    self.output,
                    outside,
                    version=VERSION,
                    firmware_sha256=FIRMWARE_SHA,
                    source_commit=SOURCE_COMMIT,
                    device=DEVICE,
                    hardware="Raspiaudio Muse Luxe ESP32",
                    observer="Household release reviewer",
                    started_at=valid_evidence()["started_at"],
                    finished_at=valid_evidence()["finished_at"],
                    rollback_sha256="c" * 64,
                    rollback_md5=ROLLBACK_MD5,
                    rollback_size=1900000,
                )
        finally:
            for path in outside.glob("*"):
                path.unlink()
            outside.rmdir()
        self.assertFalse(self.output.exists())

    def test_invalid_metrics_leave_no_output_or_temporary_file(self) -> None:
        draft = valid_evidence()
        draft["tests"]["tts_cycles"]["heard"] = 99
        draft["tests"]["rollback_artifact"]["stored_offline"] = True
        self.draft.write_text(json.dumps(draft), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.seal()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.directory.glob(".canary-core.json.*.tmp")))

    def test_sealer_overwrites_untrusted_identity_not_metrics(self) -> None:
        draft = valid_evidence()
        original_tests = deepcopy(draft["tests"])
        draft["candidate"] = {"untrusted": "identity"}
        draft["tests"]["rollback_artifact"]["stored_offline"] = True
        self.draft.write_text(json.dumps(draft), encoding="utf-8")
        sealed = self.seal()
        self.assertEqual(sealed["candidate"]["source_commit"], SOURCE_COMMIT)
        self.assertEqual(
            sealed["tests"]["tts_cycles"], original_tests["tts_cycles"]
        )

    def test_cli_orders_clean_git_candidate_and_rollback_preflights(self) -> None:
        source = (
            Path(__file__).with_name("seal_canary_core_evidence.py")
        ).read_text(encoding="utf-8")
        markers = [
            "source_commit = git_identity(root)",
            "readiness = validate_readiness(",
            "rollback_version = validate_rollback(",
            "record = seal_record(",
        ]
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("--overwrite", source)


if __name__ == "__main__":
    unittest.main()
