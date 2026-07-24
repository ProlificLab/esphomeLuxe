#!/usr/bin/env python3
"""Verify an exact retained artifact against the immutable hal.6 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def validate_rollback(artifact: Path, manifest_path: Path, expected_sha256: str) -> str:
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise RuntimeError("Rollback artifact is missing or empty")
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise RuntimeError("Rollback SHA-256 must be an exact lowercase digest")
    data = artifact.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise RuntimeError("Rollback artifact differs from the reviewed SHA-256")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("Rollback manifest must be a JSON object")
    builds = manifest.get("builds")
    build = builds[0] if isinstance(builds, list) and len(builds) == 1 else None
    ota = build.get("ota") if isinstance(build, dict) else None
    if (
        manifest.get("name") != "raspiaudio.voice-assistant"
        or manifest.get("version") != "2025.3.1-hal.6"
        or not isinstance(ota, dict)
        or ota.get("md5") != hashlib.md5(data).hexdigest()
        or ota.get("offset") != 0
    ):
        raise RuntimeError("Artifact does not match the immutable hal.6 manifest")
    return manifest["version"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--manifest", type=Path, default="manifest_update.json")
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    version = validate_rollback(args.artifact, args.manifest, args.expected_sha256)
    print(version)


if __name__ == "__main__":
    main()
