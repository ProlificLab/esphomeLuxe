#!/usr/bin/env python3
"""Validate and atomically synchronize the fixed Muse rescue WAV set."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import wave


CARD_LABEL = "MUSE_RESCUE"
MARKER = ".muse-rescue-card"
MEDIA_DIRECTORY = "RESCUE"
MAX_SECONDS = 180
CLIPS = (
    "READY.WAV",
    "POWER.WAV",
    "PWRLIST.WAV",
    "EVAC.WAV",
    "EVACLIST.WAV",
    "ALLCLEAR.WAV",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_wav(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Rescue source must be a regular file: {path}")
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            sample_rate = audio.getframerate()
            frames = audio.getnframes()
            compression = audio.getcomptype()
    except (wave.Error, EOFError) as error:
        raise ValueError(f"Invalid WAV file: {path}: {error}") from error
    duration = frames / sample_rate if sample_rate else 0
    if (
        compression != "NONE"
        or channels != 2
        or sample_width != 2
        or sample_rate != 48000
        or duration <= 0
        or duration > MAX_SECONDS
    ):
        raise ValueError(
            f"{path.name} must be PCM s16le, 48 kHz, stereo and 0-{MAX_SECONDS}s; "
            f"got compression={compression}, channels={channels}, "
            f"width={sample_width}, rate={sample_rate}, duration={duration:.3f}s"
        )
    return {
        "name": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "duration_seconds": round(duration, 3),
    }


def validate_destination(destination: Path, initialize: bool) -> Path:
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("Destination must be an existing, non-symlink directory")
    destination = destination.resolve()
    marker = destination / MARKER
    if initialize:
        if destination.name != CARD_LABEL:
            raise ValueError(
                f"Initialization is allowed only on a volume named {CARD_LABEL}"
            )
        marker.write_text(
            json.dumps({"format": 1, "purpose": "muse-offline-rescue"}) + "\n",
            encoding="ascii",
        )
    if not marker.is_file() or marker.is_symlink():
        raise ValueError(
            f"Destination is not an initialized Muse rescue card: missing {MARKER}"
        )
    marker_data = json.loads(marker.read_text(encoding="ascii"))
    if marker_data != {"format": 1, "purpose": "muse-offline-rescue"}:
        raise ValueError("Destination marker has an unexpected format or purpose")
    return destination


def synchronize(source: Path, destination: Path, initialize: bool = False) -> dict:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Source must be an existing, non-symlink directory")
    source = source.resolve()

    metadata = []
    for name in CLIPS:
        metadata.append(validate_wav(source / name))

    # Never mark a destination as initialized until the complete source set is valid.
    destination = validate_destination(destination, initialize)

    media_destination = destination / MEDIA_DIRECTORY
    media_destination.mkdir(mode=0o755, exist_ok=True)
    if media_destination.is_symlink():
        raise ValueError("Rescue media destination must not be a symlink")

    for item in metadata:
        source_path = source / item["name"]
        final_path = media_destination / item["name"]
        temporary_path = media_destination / f".{item['name']}.new"
        with source_path.open("rb") as input_file, temporary_path.open("wb") as output_file:
            shutil.copyfileobj(input_file, output_file, 1024 * 1024)
            output_file.flush()
            os.fsync(output_file.fileno())
        if sha256(temporary_path) != item["sha256"]:
            temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Checksum mismatch while copying {item['name']}")
        os.replace(temporary_path, final_path)

    manifest = {
        "format": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audio": {
            "codec": "pcm_s16le",
            "sample_rate": 48000,
            "channels": 2,
            "maximum_clip_seconds": MAX_SECONDS,
        },
        "files": metadata,
    }
    manifest_tmp = media_destination / ".manifest.json.new"
    manifest_path = media_destination / "manifest.json"
    manifest_tmp.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    os.replace(manifest_tmp, manifest_path)

    for item in metadata:
        copied = media_destination / item["name"]
        if sha256(copied) != item["sha256"]:
            raise RuntimeError(f"Post-copy checksum mismatch: {item['name']}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--initialize",
        action="store_true",
        help=f"Create the marker only when destination is named {CARD_LABEL}",
    )
    args = parser.parse_args()
    result = synchronize(args.source, args.destination, args.initialize)
    print(json.dumps({"status": "ready", "files": result["files"]}, indent=2))


if __name__ == "__main__":
    main()
