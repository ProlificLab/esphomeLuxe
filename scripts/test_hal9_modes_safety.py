#!/usr/bin/env python3
"""Negative source fixtures for the hal.9 mode qualification contract."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from check_hal9_modes_safety import validate


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "scripts/test_hal9_modes.py").read_text(encoding="utf-8")
VALIDATOR = (ROOT / "scripts/check_hal9_modes_evidence.py").read_text(
    encoding="utf-8"
)
FIRMWARE = (ROOT / "packages/recovery.yaml").read_text(encoding="utf-8")
VOICE = (ROOT / "packages/voice.yaml").read_text(encoding="utf-8")


class ModesSafetyTests(unittest.TestCase):
    def check(
        self,
        runtime: str = RUNTIME,
        validator: str = VALIDATOR,
        firmware: str = FIRMWARE,
        voice: str = VOICE,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime_path = root / "runtime.py"
            validator_path = root / "validator.py"
            firmware_path = root / "recovery.yaml"
            voice_path = root / "voice.yaml"
            runtime_path.write_text(runtime, encoding="utf-8")
            validator_path.write_text(validator, encoding="utf-8")
            firmware_path.write_text(firmware, encoding="utf-8")
            voice_path.write_text(voice, encoding="utf-8")
            validate(runtime_path, validator_path, firmware_path, voice_path)

    def test_current_sources_pass(self) -> None:
        self.check()

    def test_missing_guards_fail(self) -> None:
        mutations = (
            ("Active timers present", "Timer check removed"),
            ("finally:", "if False:"),
            ("safe cleanup", "unchecked cleanup"),
            ("cleanup_revisions", "revision_guard_removed"),
            ("os.replace(temporary_name, path)", "path.write_text('unsafe')"),
            ("before != after", "before == after"),
        )
        for old, new in mutations:
            runtime = RUNTIME.replace(old, new)
            validator = VALIDATOR.replace(old, new)
            with self.subTest(marker=old), self.assertRaises(RuntimeError):
                self.check(runtime, validator)

    def test_optional_version_or_output_fails(self) -> None:
        for marker in ("--expected-version", "--output"):
            mutated = RUNTIME.replace(
                f'parser.add_argument("{marker}", required=True)',
                f'parser.add_argument("{marker}")',
            ).replace(
                f'parser.add_argument("{marker}", type=Path, required=True)',
                f'parser.add_argument("{marker}", type=Path)',
            )
            with self.subTest(marker=marker), self.assertRaises(RuntimeError):
                self.check(mutated)

    def test_publication_before_cleanup_fails(self) -> None:
        publication = "    write_evidence(args.output, evidence, args.overwrite)"
        mutated = RUNTIME.replace(publication, "")
        mutated = mutated.replace("    finally:\n", publication + "\n    finally:\n", 1)
        with self.assertRaises(RuntimeError):
            self.check(mutated)

    def test_firmware_health_drift_fails(self) -> None:
        mutated = FIRMWARE.replace(
            'case ${P_answering}: return {"busy"};',
            'case ${P_answering}: return {"healthy"};',
        )
        with self.assertRaises(RuntimeError):
            self.check(firmware=mutated)

    def test_api_switch_drift_fails(self) -> None:
        for marker in (
            "id: privacy_mode_switch",
            "restore_mode: RESTORE_DEFAULT_OFF",
            "script.execute: start_continuous_conversation",
            "script.execute: stop_continuous_conversation",
        ):
            mutated = VOICE.replace(marker, "removed_mode_contract", 1)
            with self.subTest(marker=marker), self.assertRaises(RuntimeError):
                self.check(voice=mutated)


if __name__ == "__main__":
    unittest.main()
