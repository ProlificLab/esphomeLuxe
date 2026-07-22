#!/usr/bin/env python3
"""Bind the alpha.6 corrective candidate to its exact incident and source CI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from check_build_metadata import validate_metadata
from check_canary_deploy_readiness import validate_candidate
from check_corrective_incident import OLD_VERSION, validate_record
from check_source_ci_preflight import validate as validate_ci


NEW_VERSION = "2025.3.1-hal.9.0-alpha.6"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_readiness(
    artifact: Path,
    manifest: Path,
    build_metadata: Path,
    incident: Path,
    raw_jsonl: Path,
    old_artifact: Path,
    source_ci: Path,
    new_sha256: str,
    old_sha256: str,
    source_commit: str,
) -> dict[str, object]:
    candidate = validate_candidate(artifact, manifest, new_sha256)
    if candidate["version"] != NEW_VERSION:
        raise RuntimeError("Corrective canary requires the exact alpha.6 version")
    metadata = validate_metadata(
        build_metadata, artifact, source_commit, Path(__file__).resolve().parents[1]
    )
    if metadata["version"] != NEW_VERSION:
        raise RuntimeError("Corrective build metadata version differs from alpha.6")
    record = validate_record(incident, raw_jsonl, old_artifact, old_sha256)
    if record["old_version"] != OLD_VERSION or OLD_VERSION == NEW_VERSION:
        raise RuntimeError("Corrective transition version identity is invalid")
    ci = validate_ci(source_ci, source_commit)
    return {
        "schema_version": 1,
        "passed": True,
        "old_version": OLD_VERSION,
        "new_version": NEW_VERSION,
        "old_firmware_sha256": old_sha256,
        "new_firmware_sha256": candidate["sha256"],
        "incident_record_sha256": digest(incident),
        "build_metadata_sha256": digest(build_metadata),
        "raw_sha256": record["raw_sha256"],
        "source_commit": source_commit,
        "source_ci_run_id": ci["run_id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("build_metadata", type=Path)
    parser.add_argument("incident", type=Path)
    parser.add_argument("raw_jsonl", type=Path)
    parser.add_argument("old_artifact", type=Path)
    parser.add_argument("source_ci", type=Path)
    parser.add_argument("--new-sha256", required=True)
    parser.add_argument("--old-sha256", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = validate_readiness(
        args.artifact, args.manifest, args.build_metadata, args.incident, args.raw_jsonl,
        args.old_artifact, args.source_ci, args.new_sha256, args.old_sha256,
        args.source_commit,
    )
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            f"Corrective canary ready: {result['old_version']} -> {result['new_version']} "
            f"sha256={result['new_firmware_sha256']}."
        )


if __name__ == "__main__":
    main()
