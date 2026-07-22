#!/usr/bin/env python3
"""Bind a rotated canary OTA to its exact private build credentials."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path

from check_secret_rotation_bundle import validate_bundle
from check_source_qualification_evidence import validate_evidence


def fail(message: str) -> None:
    raise RuntimeError(message)


def digest(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        fail("Rotated candidate input must be a non-empty regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_binding(
    artifact: Path,
    source_evidence: Path,
    rotation_directory: Path,
    expected_version: str,
) -> dict[str, object]:
    validate_bundle(rotation_directory)
    firmware_sha = digest(artifact)
    digest(source_evidence)
    secrets_sha = digest(rotation_directory / "secrets.yaml")
    evidence = validate_evidence(
        source_evidence,
        expected_version=expected_version,
        expected_firmware_sha256=firmware_sha,
        expected_size_bytes=artifact.stat().st_size,
        expected_secrets_sha256=secrets_sha,
    )
    recorded_sha = evidence["credentials"]["file_sha256"]
    if not hmac.compare_digest(recorded_sha, secrets_sha):
        fail("Rotated candidate was not built with the reviewed new credentials")
    return {
        "schema_version": 1,
        "passed": True,
        "project_version": expected_version,
        "firmware_sha256": firmware_sha,
        "credentials_bound": True,
        "build_count": evidence["build"]["count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("source_evidence", type=Path)
    parser.add_argument("rotation_directory", type=Path)
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    result = validate_binding(
        args.artifact, args.source_evidence, args.rotation_directory,
        args.expected_version,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
