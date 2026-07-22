#!/usr/bin/env python3
"""Atomically derive and seal exact source-qualification evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from check_source_qualification_evidence import (
    ESPHOME_IMAGE,
    HAL6_BASELINE_BYTES,
    HARD_PERCENT,
    PARTITION_BYTES,
    TARGET_PERCENT,
    validate_evidence,
)


LOG_FILES = {
    "ci": "ci.log",
    "build_first": "build-first.log",
    "build_second": "build-second.log",
    "firmware_size": "firmware-size.log",
    "secrets_audit": "secrets-audit.log",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def git_identity(root: Path) -> str:
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
        check=True, capture_output=True, text=True,
    ).stdout
    if status:
        fail("Source evidence sealing requires a clean Git worktree")
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        fail("Source evidence commit is not a full lowercase SHA")
    return commit


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind_logs(logs_dir: Path, output_dir: Path) -> tuple[dict[str, str], dict[str, Path]]:
    root = output_dir.resolve()
    bindings: dict[str, str] = {}
    paths: dict[str, Path] = {}
    for name, filename in LOG_FILES.items():
        supplied_path = logs_dir / filename
        if supplied_path.is_symlink():
            fail(f"Source raw log must not be a symlink: {filename}")
        path = supplied_path.resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            fail(f"Source raw log must remain inside evidence directory: {filename}")
        if not path.is_file() or path.stat().st_size == 0 or path in paths.values():
            fail(f"Source raw log is missing, empty or duplicated: {filename}")
        paths[name] = path
        bindings[name] = f"sha256:{digest(path)} {relative}"
    return bindings, paths


def parse_size(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def derive_record(
    output_path: Path, logs_dir: Path, artifact: Path, version: str,
    source_commit: str, reviewer: str, private_secrets: Path,
) -> dict[str, object]:
    if output_path.exists() or output_path.is_symlink():
        fail(f"Refusing to overwrite sealed source evidence: {output_path}")
    if (
        not output_path.parent.is_dir()
        or output_path.parent.is_symlink()
        or not artifact.is_file()
        or artifact.is_symlink()
        or artifact.stat().st_size == 0
    ):
        fail("Source evidence output directory or OTA artifact is invalid")
    if (
        not private_secrets.is_file()
        or private_secrets.is_symlink()
        or private_secrets.stat().st_uid != os.getuid()
        or private_secrets.stat().st_mode & 0o777 != 0o600
    ):
        fail("Source evidence private secrets must be current-user mode 0600")
    firmware_sha = digest(artifact)
    secrets_sha = digest(private_secrets)
    bindings, paths = bind_logs(logs_dir, output_path.parent)
    ci = json.loads(paths["ci"].read_text(encoding="utf-8"))
    jobs = ci.get("jobs") if isinstance(ci, dict) else None
    job = next((item for item in jobs or [] if isinstance(item, dict) and item.get("name") == "compile"), None)
    if not isinstance(job, dict):
        fail("Source CI log has no compile job")
    for name in ("build_first", "build_second"):
        build_log = paths[name].read_text(encoding="utf-8")
        if firmware_sha not in build_log:
            fail(f"Source {name} log does not contain exact OTA SHA-256")
        if f"SECRETS SHA256={secrets_sha}" not in build_log.splitlines():
            fail(f"Source {name} log does not bind the selected private secrets")
    size_values = parse_size(paths["firmware_size"])
    size = artifact.stat().st_size
    required_size = {
        "size_bytes": str(size), "partition_bytes": str(PARTITION_BYTES),
        "usage_percent": f"{size * 1000 // PARTITION_BYTES / 10:.1f}",
        "target_percent": str(TARGET_PERCENT), "hard_percent": str(HARD_PERCENT),
        "hal6_baseline_bytes": str(HAL6_BASELINE_BYTES),
    }
    if any(size_values.get(key) != value for key, value in required_size.items()):
        fail("Source firmware-size log differs from exact OTA metrics")
    secret = json.loads(paths["secrets_audit"].read_text(encoding="utf-8"))
    findings = secret.get("findings") if isinstance(secret, dict) else None
    if not isinstance(findings, dict):
        fail("Source secret-audit log is invalid")
    return {
        "schema_version": 2, "passed": True,
        "candidate": {"project_version": version, "firmware_sha256": firmware_sha, "source_commit": source_commit},
        "reviewer": reviewer, "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "logs": bindings,
        "ci": {
            "repository": "ProlificLab/esphomeLuxe", "workflow": ci.get("name"),
            "run_id": ci.get("databaseId"), "job_id": job.get("databaseId"),
            "head_sha": ci.get("headSha"), "conclusion": ci.get("conclusion"),
            "event": ci.get("event"), "url": ci.get("url"),
        },
        "build": {
            "count": 2, "first_sha256": firmware_sha, "second_sha256": firmware_sha,
            "reproducible": True, "size_bytes": size, "partition_bytes": PARTITION_BYTES,
            "usage_percent": size * 1000 // PARTITION_BYTES / 10,
            "target_percent": TARGET_PERCENT, "hard_percent": HARD_PERCENT,
            "hal6_baseline_bytes": HAL6_BASELINE_BYTES,
            "target_passed": size <= PARTITION_BYTES * TARGET_PERCENT // 100,
            "hard_limit_passed": size <= PARTITION_BYTES * HARD_PERCENT // 100,
            "container_image": ESPHOME_IMAGE, "esp_idf": "5.4.2",
        },
        "credentials": {
            "file_sha256": secrets_sha, "mounted_path": "/config/secrets.yaml",
            "read_only": True, "builds_bound": 2,
        },
        "secrets_audit": {
            "tracked_file_count": secret.get("tracked_file_count"),
            "private_secret_keys_checked": secret.get("private_secret_keys_checked"),
            "exact_secret_matches": len(findings.get("exact_secret_matches", [])),
            "suspicious_pattern_matches": len(findings.get("suspicious_pattern_matches", [])),
            "prohibited_tracked_files": len(findings.get("prohibited_tracked_files", [])),
        },
    }


def seal(record: dict[str, object], output_path: Path) -> None:
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent,
                                         prefix=f".{output_path.name}.", suffix=".tmp", delete=False) as output:
            json.dump(record, output, indent=2, sort_keys=True); output.write("\n")
            output.flush(); os.fsync(output.fileno()); temporary_name = output.name
        temporary = Path(temporary_name)
        candidate = record["candidate"]
        validate_evidence(temporary, candidate["project_version"], candidate["firmware_sha256"],
                          candidate["source_commit"], record["build"]["size_bytes"])
        try:
            os.link(temporary, output_path)
        except FileExistsError:
            fail(f"Refusing to overwrite concurrently sealed source evidence: {output_path}")
        temporary.unlink(); temporary_name = None
        directory_fd = os.open(output_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path); parser.add_argument("artifact", type=Path)
    parser.add_argument("version"); parser.add_argument("--logs-dir", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--private-secrets", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    record = derive_record(args.output, args.logs_dir, args.artifact, args.version,
                           git_identity(root), args.reviewer, args.private_secrets)
    seal(record, args.output)
    print(f"Sealed source qualification: path={args.output} sha256={digest(args.output)}")


if __name__ == "__main__":
    main()
