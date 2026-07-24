#!/usr/bin/env python3
"""Unit tests for guarded rescue-card preparation."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import wave

import prepare_rescue_media as rescue


def make_wav(path: Path, *, channels: int = 2, rate: int = 48000) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b"\0\0" * channels * (rate // 20))


class RescueMediaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        for name in rescue.CLIPS:
            make_wav(self.source / name)
        self.destination = self.root / rescue.CARD_LABEL
        self.destination.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_synchronizes_fixed_set_with_manifest(self) -> None:
        manifest = rescue.synchronize(self.source, self.destination, initialize=True)
        self.assertEqual(len(manifest["files"]), len(rescue.CLIPS))
        stored = json.loads(
            (self.destination / rescue.MEDIA_DIRECTORY / "manifest.json").read_text()
        )
        self.assertEqual([item["name"] for item in stored["files"]], list(rescue.CLIPS))
        for item in stored["files"]:
            self.assertEqual(
                rescue.sha256(self.destination / rescue.MEDIA_DIRECTORY / item["name"]),
                item["sha256"],
            )

    def test_refuses_unmarked_destination(self) -> None:
        with self.assertRaisesRegex(ValueError, "not an initialized"):
            rescue.synchronize(self.source, self.destination)

    def test_refuses_initializing_wrong_volume_name(self) -> None:
        wrong = self.root / "ordinary-disk"
        wrong.mkdir()
        with self.assertRaisesRegex(ValueError, "MUSE_RESCUE"):
            rescue.synchronize(self.source, wrong, initialize=True)

    def test_refuses_missing_or_wrong_format_clip(self) -> None:
        (self.source / rescue.CLIPS[0]).unlink()
        with self.assertRaisesRegex(ValueError, "regular file"):
            rescue.synchronize(self.source, self.destination, initialize=True)
        self.assertFalse((self.destination / rescue.MARKER).exists())
        make_wav(self.source / rescue.CLIPS[0], channels=1)
        with self.assertRaisesRegex(ValueError, "stereo"):
            rescue.synchronize(self.source, self.destination, initialize=True)


if __name__ == "__main__":
    unittest.main()
