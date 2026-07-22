#!/usr/bin/env python3
"""Validate local firmware build metadata against one exact artifact and commit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


ESPHOME_IMAGE = "esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
KEYS = {
    "version", "channel", "source_commit", "source_date_epoch", "config",
    "artifact", "size_bytes", "md5", "sha256", "esphome_image", "esp_idf",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def commit_epoch(root: Path, commit: str) -> int:
    try:
        value = subprocess.run(
            ["git", "-C", str(root), "show", "-s", "--format=%ct", commit],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        fail("Build metadata source commit does not exist locally")
    if re.fullmatch(r"[1-9][0-9]{8,}", value) is None:
        fail("Build metadata source epoch is invalid")
    return int(value)


def validate_metadata(
    metadata_path: Path,
    artifact: Path,
    expected_commit: str,
    root: Path,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", expected_commit) is None:
        fail("Build metadata expected commit is invalid")
    if not artifact.is_file() or artifact.is_symlink() or artifact.stat().st_size == 0:
        fail("Build metadata artifact is missing, empty or a symlink")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Build metadata JSON is invalid: {error}")
    if not isinstance(metadata, dict) or set(metadata) != KEYS:
        fail("Build metadata keys differ from schema")
    version = metadata["version"]
    if not isinstance(version, str) or re.fullmatch(
        r"[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+", version
    ) is None:
        fail("Build metadata version is invalid")
    expected_epoch = commit_epoch(root, expected_commit)
    expected_name = f"muse-luxe-{version}.ota.bin"
    if (
        metadata["channel"] != "development"
        or metadata["source_commit"] != expected_commit
        or type(metadata["source_date_epoch"]) is not int
        or metadata["source_date_epoch"] != expected_epoch
        or metadata["config"] != "luxe_microWW.yaml"
        or metadata["artifact"] != expected_name
        or artifact.name != expected_name
        or type(metadata["size_bytes"]) is not int
        or metadata["size_bytes"] != artifact.stat().st_size
        or metadata["md5"] != digest(artifact, "md5")
        or metadata["sha256"] != digest(artifact, "sha256")
        or metadata["esphome_image"] != ESPHOME_IMAGE
        or metadata["esp_idf"] != "5.4.2"
    ):
        fail("Build metadata does not bind the exact deterministic artifact")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    metadata = validate_metadata(args.metadata, args.artifact, args.expected_commit, root)
    print(
        f"Build metadata passed: version={metadata['version']} "
        f"sha256={metadata['sha256']} epoch={metadata['source_date_epoch']}."
    )


if __name__ == "__main__":
    main()
