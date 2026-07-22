#!/usr/bin/env python3
"""Offline fixtures for canonical hal.6 USB image composition."""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import compose_hal6_usb_recovery as composer


class ComposeHal6UsbRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ota = self.root / "hal6.ota.bin"
        self.donor = self.root / "donor.factory.bin"
        self.output = self.root / "hal6.factory.bin"
        self.manifest = self.root / "manifest.json"

        self.ota_data = b"\xe9reviewed-hal6-application"
        prefix = bytearray(b"\xff" * composer.APP_OFFSET)
        prefix[0x1000] = 0xE9
        prefix[0x8000:0x8002] = b"\xaa\x50"
        self.prefix = bytes(prefix)
        self.ota.write_bytes(self.ota_data)
        self.donor.write_bytes(self.prefix + b"\xe9donor-application")
        self.manifest.write_text(json.dumps({
            "name": "raspiaudio.voice-assistant",
            "version": "2025.3.1-hal.6",
            "builds": [{"ota": {
                "md5": hashlib.md5(self.ota_data).hexdigest(),
                "offset": 0,
            }}],
        }), encoding="utf-8")
        self.ota_sha256 = hashlib.sha256(self.ota_data).hexdigest()
        self.prefix_sha256 = hashlib.sha256(self.prefix).hexdigest()
        self.factory_sha256 = hashlib.sha256(self.prefix + self.ota_data).hexdigest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def compose(self) -> dict[str, object]:
        with ExitStack() as patches:
            patches.enter_context(patch.object(composer, "HAL6_OTA_SHA256", self.ota_sha256))
            patches.enter_context(
                patch.object(composer, "HAL6_PREFIX_SHA256", self.prefix_sha256)
            )
            patches.enter_context(
                patch.object(composer, "HAL6_FACTORY_SHA256", self.factory_sha256)
            )
            return composer.compose(self.ota, self.donor, self.manifest, self.output)

    def test_exact_composition_is_private_atomic_and_canonical(self) -> None:
        result = self.compose()
        self.assertEqual(self.output.read_bytes(), self.prefix + self.ota_data)
        self.assertEqual(os.stat(self.output).st_mode & 0o777, 0o600)
        self.assertEqual(result["factory_sha256"], self.factory_sha256)
        self.assertFalse(any(self.root.glob(f".{self.output.name}.*.tmp")))

    def test_existing_output_is_never_overwritten(self) -> None:
        self.output.write_bytes(b"keep")
        with self.assertRaises(RuntimeError):
            self.compose()
        self.assertEqual(self.output.read_bytes(), b"keep")

    def test_wrong_donor_prefix_fails_without_output(self) -> None:
        data = bytearray(self.donor.read_bytes())
        data[0x2000] ^= 1
        self.donor.write_bytes(data)
        with self.assertRaises(RuntimeError):
            self.compose()
        self.assertFalse(self.output.exists())

    def test_wrong_ota_fails_without_output(self) -> None:
        self.ota.write_bytes(self.ota_data + b"changed")
        with self.assertRaises(RuntimeError):
            self.compose()
        self.assertFalse(self.output.exists())

    def test_symlink_donor_fails(self) -> None:
        target = self.root / "donor-target.bin"
        self.donor.rename(target)
        self.donor.symlink_to(target)
        with self.assertRaises(RuntimeError):
            self.compose()

    def test_short_donor_fails_without_output(self) -> None:
        self.donor.write_bytes(self.prefix)
        with self.assertRaises(RuntimeError):
            self.compose()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
