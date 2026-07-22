#!/usr/bin/env python3
"""Structural safety tests for canonical hal.6 USB flashing."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/flash_hal6_usb.sh").read_text(encoding="utf-8")


class Hal6UsbFlashSafetyTests(unittest.TestCase):
    def test_validation_surrounds_exact_confirmation(self) -> None:
        function = SCRIPT.index("validate()")
        first = SCRIPT.index("validate\n", function)
        confirmation = SCRIPT.index('confirmation="FLASH HAL6 USB', first)
        second = SCRIPT.index("validate\n", confirmation)
        flash = SCRIPT.index("write-flash 0x0", second)
        self.assertEqual([first, confirmation, second, flash], sorted((first, confirmation, second, flash)))

    def test_only_explicit_local_character_devices_are_allowed(self) -> None:
        self.assertIn('/dev/cu.*|/dev/tty.*', SCRIPT)
        self.assertIn('! -c "$SERIAL_PORT"', SCRIPT)
        self.assertIn('-L "$SERIAL_PORT"', SCRIPT)
        confirmation = SCRIPT.index('confirmation="FLASH HAL6 USB')
        self.assertLess(SCRIPT.index("validate_serial\n"), confirmation)
        self.assertGreater(SCRIPT.index("validate_serial\n", confirmation), confirmation)

    def test_esptool_is_version_pinned_and_keeps_verification(self) -> None:
        self.assertIn("--with esptool==5.3.1", SCRIPT)
        self.assertIn("--chip esp32", SCRIPT)
        self.assertIn("--baud 460800", SCRIPT)
        self.assertNotIn("--force", SCRIPT)
        self.assertNotIn("--erase-all", SCRIPT)
        self.assertNotIn("--no-verify", SCRIPT)

    def test_no_network_ota_or_secret_material_is_used(self) -> None:
        self.assertNotIn("espota", SCRIPT)
        self.assertNotIn("esphome upload", SCRIPT)
        self.assertNotIn("secrets.yaml", SCRIPT)
        self.assertNotIn("read-flash", SCRIPT)


if __name__ == "__main__":
    unittest.main()
