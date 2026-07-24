#!/usr/bin/env python3
"""Offline fixtures for the immutable hal.6 USB recovery gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_hal6_usb_recovery as checker


class Hal6UsbRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ota = self.root / "hal6.ota.bin"
        self.factory = self.root / "hal6.factory.bin"
        self.manifest = self.root / "manifest.json"
        self.ota.write_bytes(b"\xe9reviewed-hal6-application")
        prefix = bytearray(b"\xff" * checker.APP_OFFSET)
        prefix[0x1000] = 0xE9
        prefix[0x8000:0x8002] = b"\xaa\x50"
        self.prefix = bytes(prefix)
        self.factory.write_bytes(self.prefix + self.ota.read_bytes())
        self.manifest.write_text(json.dumps({
            "name": "raspiaudio.voice-assistant",
            "version": "2025.3.1-hal.6",
            "builds": [{"ota": {
                "md5": hashlib.md5(self.ota.read_bytes()).hexdigest(),
                "offset": 0,
            }}],
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self) -> dict[str, object]:
        with patch.object(
            checker, "HAL6_OTA_SHA256", hashlib.sha256(self.ota.read_bytes()).hexdigest()
        ), patch.object(
            checker,
            "HAL6_FACTORY_SHA256",
            hashlib.sha256(self.factory.read_bytes()).hexdigest(),
        ):
            return checker.validate_usb_recovery(self.ota, self.factory, self.manifest)

    def test_exact_factory_embedding_passes(self) -> None:
        result = self.validate()
        self.assertTrue(result["passed"])
        self.assertEqual(result["app_offset"], 0x10000)
        self.assertEqual(result["factory_bytes"], checker.APP_OFFSET + result["ota_bytes"])

    def test_factory_digest_mismatch_fails(self) -> None:
        with patch.object(
            checker, "HAL6_OTA_SHA256", hashlib.sha256(self.ota.read_bytes()).hexdigest()
        ), patch.object(
            checker, "HAL6_FACTORY_SHA256", "0" * 64
        ), self.assertRaises(RuntimeError):
            checker.validate_usb_recovery(self.ota, self.factory, self.manifest)

    def test_wrong_offset_or_trailing_data_fails(self) -> None:
        for data in (
            self.prefix[:-1] + self.ota.read_bytes(),
            self.factory.read_bytes() + b"trailing",
        ):
            with self.subTest(size=len(data)):
                self.factory.write_bytes(data)
                with self.assertRaises(RuntimeError):
                    self.validate()

    def test_modified_embedded_ota_fails(self) -> None:
        data = bytearray(self.factory.read_bytes())
        data[-1] ^= 1
        self.factory.write_bytes(data)
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_invalid_partition_marker_fails(self) -> None:
        data = bytearray(self.factory.read_bytes())
        data[0x8000:0x8002] = b"\0\0"
        self.factory.write_bytes(data)
        with self.assertRaisesRegex(RuntimeError, "partition"):
            self.validate()

    def test_modified_archived_ota_fails_before_embedding_check(self) -> None:
        reviewed_sha256 = hashlib.sha256(self.ota.read_bytes()).hexdigest()
        self.ota.write_bytes(self.ota.read_bytes() + b"changed")
        with patch.object(
            checker, "HAL6_OTA_SHA256", reviewed_sha256
        ), patch.object(
            checker,
            "HAL6_FACTORY_SHA256",
            hashlib.sha256(self.factory.read_bytes()).hexdigest(),
        ), self.assertRaisesRegex(RuntimeError, "immutable hal.6 SHA-256"):
            checker.validate_usb_recovery(self.ota, self.factory, self.manifest)

    def test_symlink_inputs_fail(self) -> None:
        target = self.root / "factory-target.bin"
        self.factory.rename(target)
        self.factory.symlink_to(target)
        with self.assertRaises(RuntimeError):
            self.validate()

    def test_manifest_md5_and_ota_digest_are_both_required(self) -> None:
        changed = json.loads(self.manifest.read_text(encoding="utf-8"))
        changed["builds"][0]["ota"]["md5"] = "0" * 32
        self.manifest.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.validate()


if __name__ == "__main__":
    unittest.main()
