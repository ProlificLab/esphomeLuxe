#!/usr/bin/env python3
"""Negative fixtures for voice no-speech classification."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from check_voice_error_classification import validate


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "voice": "packages/voice.yaml",
    "recovery": "packages/recovery.yaml",
    "diagnostics": "packages/diagnostics.yaml",
    "monitor": "scripts/monitor_endurance.py",
    "summary": "scripts/check_endurance_summary.py",
}
SOURCES = {name: (ROOT / path).read_text(encoding="utf-8") for name, path in FILES.items()}


class VoiceErrorClassificationTests(unittest.TestCase):
    def check(self, **changes: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = {}
            for name, relative in FILES.items():
                path = Path(temporary) / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(changes.get(name, SOURCES[name]), encoding="utf-8")
                paths[name] = path
            validate(
                paths["voice"],
                paths["recovery"],
                paths["diagnostics"],
                paths["monitor"],
                paths["summary"],
            )

    def test_current_sources_pass(self) -> None:
        self.check()

    def test_open_or_wrong_code_fails(self) -> None:
        mutated = SOURCES["voice"].replace(
            'code == "stt-no-text-recognized"', 'code.find("stt-") == 0'
        )
        with self.assertRaises(RuntimeError):
            self.check(voice=mutated)

    def test_no_speech_cannot_become_error_or_recovery(self) -> None:
        marker = "          id(voice_no_speech_count)++;"
        for replacement in (
            marker + "\n          id(voice_error_count)++;",
            marker + "\n          id(recover_voice).execute(\"voice_error\");",
        ):
            mutated = SOURCES["voice"].replace(marker, replacement, 1)
            with self.subTest(replacement=replacement), self.assertRaises(RuntimeError):
                self.check(voice=mutated)

    def test_real_errors_keep_degraded_recovery(self) -> None:
        for source, marker in (
            ("voice", "id(set_phase).execute(${P_error});"),
            ("voice", "id(handle_voice_error).execute();"),
            ("recovery", "reason: voice_error"),
        ):
            mutated = SOURCES[source].replace(marker, "removed_real_error_guard", 1)
            with self.subTest(marker=marker), self.assertRaises(RuntimeError):
                self.check(**{source: mutated})

    def test_diagnostics_and_bound_cannot_be_removed_or_relaxed(self) -> None:
        mutations = (
            ("diagnostics", "id: voice_no_speech_counter", "id: removed_counter"),
            ("recovery", "id: voice_no_speech_count", "id: removed_count"),
            (
                "monitor",
                'parser.add_argument("--max-new-no-speech", type=float, default=3)',
                'parser.add_argument("--max-new-no-speech", type=float, default=4)',
            ),
            (
                "monitor",
                'parser.add_argument("--max-new-recoveries", type=float, default=0)',
                'parser.add_argument("--max-new-recoveries", type=float, default=1)',
            ),
            ("summary", '"max_new_no_speech": 3', '"max_new_no_speech": 4'),
        )
        for name, old, new in mutations:
            mutated = SOURCES[name].replace(old, new, 1)
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                self.check(**{name: mutated})


if __name__ == "__main__":
    unittest.main()
