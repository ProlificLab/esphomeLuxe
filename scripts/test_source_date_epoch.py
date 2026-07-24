#!/usr/bin/env python3
"""Close deterministic build epoch derivation and propagation."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/source_date_epoch.sh"


class SourceDateEpochTests(unittest.TestCase):
    def test_epoch_is_exact_head_commit_time(self) -> None:
        expected = subprocess.run(
            ["git", "-C", str(ROOT), "show", "-s", "--format=%ct", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        actual = subprocess.run(
            [str(SCRIPT)], check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(actual, expected)
        self.assertRegex(actual, r"^[1-9][0-9]{8,}$")

    def test_invalid_ref_fails(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "not-a-real-ref"], capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_ci_collector_and_promotion_pass_epoch_to_docker(self) -> None:
        workflow = (ROOT / ".github/workflows/firmware.yml").read_text(encoding="utf-8")
        collector = (ROOT / "scripts/collect_source_qualification.sh").read_text(encoding="utf-8")
        promotion = (ROOT / "scripts/promote_firmware_channel.sh").read_text(encoding="utf-8")
        packager = (ROOT / "scripts/package_firmware.sh").read_text(encoding="utf-8")
        self.assertIn("SOURCE_DATE_EPOCH=$(scripts/source_date_epoch.sh)", workflow)
        self.assertEqual(workflow.count("-e SOURCE_DATE_EPOCH"), 3)
        self.assertIn('source_epoch="$("$SCRIPT_DIR/source_date_epoch.sh" "$source_commit")"', collector)
        self.assertEqual(collector.count('-e SOURCE_DATE_EPOCH="$source_epoch"'), 2)
        self.assertIn("SOURCE_DATE_EPOCH=%s", collector)
        self.assertIn('source_epoch="$("$SCRIPT_DIR/source_date_epoch.sh" "$source_commit")"', promotion)
        self.assertEqual(promotion.count('-e SOURCE_DATE_EPOCH="$source_epoch"'), 2)
        self.assertIn('"source_date_epoch": $("$SCRIPT_DIR/source_date_epoch.sh")', packager)


if __name__ == "__main__":
    unittest.main()
