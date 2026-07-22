#!/usr/bin/env python3
"""Offline safety tests for Muse credential rotation preparation."""

from __future__ import annotations

import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml

from prepare_secret_rotation import ROTATED_KEYS, prepare
from monitor_endurance import write_summary
from test_endurance_summary import VERSION, valid_summary


CURRENT = {
    "api_encryption_key": base64.b64encode(b"0" * 32).decode("ascii"),
    "ota_password": "replace-with-a-long-random-password",
    "fallback_ap_password": "replace-with-random",
    "wifi_ssid": "private-household-network",
    "wifi_password": "private-household-wifi-password",
}


class PrepareSecretRotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.current = self.root / "current.yaml"
        self.current.write_text(yaml.safe_dump(CURRENT, sort_keys=False), encoding="utf-8")
        self.current.chmod(0o600)
        self.output = self.root / "rotation"
        self.endurance = self.root / "endurance-summary.json"
        write_summary(self.endurance, valid_summary())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def prepare(self, current: Path | None = None, output: Path | None = None):
        return prepare(
            current or self.current, output or self.output, self.endurance, VERSION
        )

    def test_prepares_private_independent_files_without_disclosure(self) -> None:
        captured = io.StringIO()
        with redirect_stdout(captured):
            manifest = self.prepare()
        rotated = yaml.safe_load((self.output / "secrets.yaml").read_text(encoding="utf-8"))
        transition = yaml.safe_load(
            (self.output / "transition-ota.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(rotated["wifi_ssid"], CURRENT["wifi_ssid"])
        self.assertEqual(rotated["wifi_password"], CURRENT["wifi_password"])
        self.assertEqual(set(transition), {"ota_password"})
        self.assertEqual(transition["ota_password"], CURRENT["ota_password"])
        self.assertEqual(len(base64.b64decode(rotated["api_encryption_key"], validate=True)), 32)
        self.assertEqual(len({rotated[key] for key in ROTATED_KEYS}), 3)
        for key in ROTATED_KEYS:
            self.assertNotEqual(rotated[key], CURRENT[key])
            self.assertNotIn(rotated[key], captured.getvalue())
            self.assertNotIn(rotated[key], str(manifest))
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for name in ("secrets.yaml", "transition-ota.yaml", "rotation-manifest.json"):
            self.assertEqual((self.output / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(manifest["network_actions_performed"], 0)
        self.assertTrue(manifest["endurance"]["passed"])
        self.assertEqual(manifest["endurance"]["project_version"], VERSION)
        manifest_on_disk = json.loads(
            (self.output / "rotation-manifest.json").read_text(encoding="utf-8")
        )
        for value in tuple(CURRENT.values()) + tuple(rotated[key] for key in ROTATED_KEYS):
            self.assertNotIn(value, str(manifest_on_disk))

    def test_refuses_insecure_input_and_existing_output(self) -> None:
        self.current.chmod(0o644)
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.assertFalse(self.output.exists())
        self.current.chmod(0o600)
        self.output.mkdir()
        marker = self.output / "keep"
        marker.write_text("untouched", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.assertEqual(marker.read_text(encoding="utf-8"), "untouched")

        source_link = self.root / "current-link.yaml"
        source_link.symlink_to(self.current)
        with self.assertRaises(RuntimeError):
            self.prepare(source_link, self.root / "linked-source-output")
        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        parent_link = self.root / "parent-link"
        parent_link.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            self.prepare(self.current, parent_link / "rotation")

    def test_refuses_missing_keys_and_generated_collisions(self) -> None:
        invalid = dict(CURRENT)
        invalid.pop("ota_password")
        self.current.write_text(yaml.safe_dump(invalid), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.current.write_text(yaml.safe_dump(CURRENT), encoding="utf-8")
        with mock.patch(
            "prepare_secret_rotation.generate_values",
            return_value={key: "same-generated-value-for-every-key" for key in ROTATED_KEYS},
        ), self.assertRaises(RuntimeError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_failure_removes_partial_private_directory(self) -> None:
        with mock.patch(
            "prepare_secret_rotation.write_private_json",
            side_effect=OSError("synthetic write failure"),
        ), self.assertRaises(OSError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_requires_exact_recent_complete_endurance(self) -> None:
        summary = valid_summary()
        summary["observed_duration_seconds"] = 86399
        write_summary(self.endurance, summary)
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.assertFalse(self.output.exists())

        write_summary(self.endurance, valid_summary())
        with self.assertRaises(RuntimeError):
            prepare(
                self.current, self.output, self.endurance,
                "2026.1.0-hal.10-wrong",
            )
        self.assertFalse(self.output.exists())
        with self.assertRaises(RuntimeError):
            prepare(self.current, self.output, self.endurance, "not-a-version")
        self.assertFalse(self.output.exists())

        endurance_link = self.root / "endurance-link.json"
        endurance_link.symlink_to(self.endurance)
        with self.assertRaises(RuntimeError):
            prepare(self.current, self.output, endurance_link, VERSION)

    def test_source_contains_no_network_or_device_action(self) -> None:
        source = (Path(__file__).parent / "prepare_secret_rotation.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("run_ota", "aioesphomeapi", "requests.", "socket.", "subprocess"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
