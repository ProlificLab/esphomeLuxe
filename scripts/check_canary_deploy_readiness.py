#!/usr/bin/env python3
"""Fail closed unless a canary artifact matches reviewed endurance evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from check_endurance_summary import validate_summary


PRIVATE_PREFIX = "http://10.10.30.159:8123/local/muse-luxe/channels/development/"


def fail(message: str) -> None:
    raise RuntimeError(message)


def file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_readiness(
    artifact: Path,
    manifest_path: Path,
    summary_path: Path,
    expected_firmware_sha256: str,
) -> dict[str, str]:
    result = validate_candidate(artifact, manifest_path, expected_firmware_sha256)
    summary = validate_summary(summary_path, result["version"])
    return {
        **result,
        "endurance_finished_at": summary["finished_at"],
    }


def validate_candidate(
    artifact: Path,
    manifest_path: Path,
    expected_firmware_sha256: str,
) -> dict[str, str]:
    """Validate an exact private development artifact without relaxing its gate."""
    if not artifact.is_file() or artifact.stat().st_size == 0:
        fail("Canary artifact is missing or empty")
    if re.fullmatch(r"[0-9a-f]{64}", expected_firmware_sha256) is None:
        fail("Reviewed canary SHA-256 must be an exact lowercase digest")
    actual_sha256 = file_digest(artifact, "sha256")
    if actual_sha256 != expected_firmware_sha256:
        fail("Canary artifact SHA-256 differs from the reviewed digest")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("name") != "raspiaudio.voice-assistant"
        or manifest.get("channel") != "development"
    ):
        fail("Canary deployment requires a development manifest")
    version = manifest.get("version")
    if not isinstance(version, str) or re.fullmatch(
        r"[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+", version
    ) is None:
        fail("Canary manifest version is invalid")
    builds = manifest.get("builds")
    if not isinstance(builds, list) or len(builds) != 1:
        fail("Canary manifest must contain exactly one build")
    build = builds[0]
    ota = build.get("ota") if isinstance(build, dict) else None
    if (
        not isinstance(build, dict)
        or build.get("chipFamily") != "ESP32"
        or not isinstance(ota, dict)
    ):
        fail("Canary manifest build identity is invalid")
    if ota.get("offset") != 0 or ota.get("md5") != file_digest(artifact, "md5"):
        fail("Canary manifest MD5 or OTA offset differs from the artifact")
    expected_name = f"muse-luxe-{version}.ota.bin"
    if artifact.name != expected_name:
        fail("Canary artifact filename differs from the manifest version")
    expected_url = f"{PRIVATE_PREFIX}firmware.ota.bin"
    if ota.get("path") != expected_url:
        fail("Canary manifest path is not the closed private development URL")

    return {
        "version": version,
        "sha256": actual_sha256,
        "firmware_destination": "muse-luxe/channels/development/firmware.ota.bin",
        "manifest_destination": "muse-luxe/channels/development/manifest.json",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--expected-firmware-sha256", required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = validate_readiness(
        args.artifact,
        args.manifest,
        args.summary,
        args.expected_firmware_sha256,
    )
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "Canary deployment readiness passed: "
            f"version={result['version']} sha256={result['sha256'][:16]} "
            f"endurance_finished_at={result['endurance_finished_at']}."
        )


if __name__ == "__main__":
    main()
