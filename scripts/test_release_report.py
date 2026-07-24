#!/usr/bin/env python3
"""Self-contained tests for the release change reporter."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("report_release_changes.py")


class ReleaseReportTest(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def write(self, root: Path, path: str, content: str) -> None:
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def commit(self, root: Path, message: str) -> str:
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", message)
        return self.git(root, "rev-parse", "HEAD")

    def test_dependency_and_subsystem_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Test")
            self.git(root, "config", "user.email", "test@example.invalid")
            self.write(root, "packages/hardware.yaml", "  version: 5.4.1\n")
            self.write(root, "luxe_microWW.yaml", "  min_version: 2025.2.0\n")
            base = self.commit(root, "Base")

            self.write(root, "packages/hardware.yaml", "  version: 5.4.2\n")
            self.write(root, "docs/OPERATIONS.md", "# Operations\n")
            self.write(root, "home-assistant/packages/muse.yaml", "script: {}\n")
            target = self.commit(root, "Upgrade ESP-IDF")
            output_json = root / "out/report.json"
            output_markdown = root / "out/report.md"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--base",
                    base,
                    "--target",
                    target,
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(output_markdown),
                ],
                cwd=root,
                check=True,
            )

            report = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], 1)
            self.assertEqual(report["commits"][0]["subject"], "Upgrade ESP-IDF")
            self.assertEqual(
                {item["subsystem"] for item in report["changes"]},
                {"documentation", "firmware", "home-assistant"},
            )
            self.assertIn(
                "5.4.2", {item["value"] for item in report["dependencies"]["added"]}
            )
            self.assertIn(
                "5.4.1",
                {item["value"] for item in report["dependencies"]["removed"]},
            )
            self.assertIn("## Dependency changes", output_markdown.read_text())

    def test_first_release_uses_empty_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Test")
            self.git(root, "config", "user.email", "test@example.invalid")
            self.write(root, "README.md", "first\n")
            self.commit(root, "Initial")
            output_json = root / "report.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(root / "report.md"),
                ],
                cwd=root,
                check=True,
            )
            report = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(report["base"]["label"], "initial release")
            self.assertEqual(len(report["commits"]), 1)
            self.assertEqual(report["changes"][0]["path"], "README.md")


if __name__ == "__main__":
    unittest.main()
