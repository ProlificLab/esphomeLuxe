#!/usr/bin/env python3
"""Offline mutation tests for the hal.6 USB provenance record."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from check_hal6_recovery_manifest import EXPECTED, validate


ROOT = Path(__file__).resolve().parents[1]


class Hal6RecoveryManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "recovery.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, value: dict[str, object]) -> None:
        self.path.write_text(json.dumps(value), encoding="utf-8")

    def test_tracked_manifest_and_source_provenance_pass(self) -> None:
        result = validate(ROOT / "docs/hal6-usb-recovery-manifest.json", ROOT)
        self.assertTrue(result["passed"])
        self.assertEqual(result["source_commits_verified"], 2)

    def test_each_identity_mutation_fails(self) -> None:
        mutations = (
            ("version", "2025.3.1-hal.5"),
            ("factory_sha", "0" * 64),
            ("app_offset", 0x20000),
            ("container", "esphome/esphome:latest"),
        )
        for name, replacement in mutations:
            value = deepcopy(EXPECTED)
            if name == "version":
                value["version"] = replacement
            elif name == "factory_sha":
                value["artifacts"]["factory"]["sha256"] = replacement
            elif name == "app_offset":
                value["layout"]["app_offset"] = replacement
            else:
                value["source"]["esphome_image"] = replacement
            self.write(value)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                validate(self.path, ROOT)

    def test_extra_or_missing_fields_fail(self) -> None:
        extra = deepcopy(EXPECTED)
        extra["unexpected"] = True
        missing = deepcopy(EXPECTED)
        missing.pop("version")
        for value in (extra, missing):
            self.write(value)
            with self.assertRaises(RuntimeError):
                validate(self.path, ROOT)

    def test_symlink_fails(self) -> None:
        target = Path(self.temporary.name) / "target.json"
        target.write_text(json.dumps(EXPECTED), encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaises(RuntimeError):
            validate(self.path, ROOT)


if __name__ == "__main__":
    unittest.main()
