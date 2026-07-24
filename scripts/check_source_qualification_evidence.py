#!/usr/bin/env python3
"""Validate hash-bound build, CI, size and tracked-secret evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re


PARTITION_BYTES = 2031616
TARGET_PERCENT = 93
HARD_PERCENT = 97
HAL6_BASELINE_BYTES = 1948144
ESPHOME_IMAGE = (
    "esphome/esphome@sha256:"
    "def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
)
LOG_NAMES = {"ci", "build_first", "build_second", "firmware_size", "secrets_audit"}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def exact_keys(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"Source qualification {label} keys differ from schema")
    return value


def require_text(value: object, label: str, minimum: int = 3) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Source qualification {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Source qualification {label} is still a placeholder")
    return text


def parse_reviewed_at(value: object) -> datetime:
    text = require_text(value, "reviewed_at")
    try:
        reviewed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Source qualification reviewed_at is invalid: {error}")
    if reviewed.tzinfo is None:
        fail("Source qualification reviewed_at must include a timezone")
    reviewed = reviewed.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if reviewed > now + timedelta(minutes=5) or reviewed < now - timedelta(days=30):
        fail("Source qualification reviewed_at is outside the 30-day review window")
    return reviewed


def resolve_logs(record_path: Path, value: object) -> dict[str, Path]:
    bindings = exact_keys(value, LOG_NAMES, "logs")
    root = record_path.parent.resolve()
    paths: dict[str, Path] = {}
    for name, binding in bindings.items():
        if not isinstance(binding, str):
            fail(f"Source qualification log {name} binding is not text")
        match = re.fullmatch(r"sha256:([0-9a-f]{64})\s+(.+)", binding)
        if match is None:
            fail(f"Source qualification log {name} is not hash-bound")
        expected, relative_name = match.groups()
        relative = Path(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            fail(f"Source qualification log {name} path is unsafe")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size == 0:
            fail(f"Source qualification log {name} is missing or empty")
        if path in paths.values():
            fail("Source qualification logs must be five distinct files")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            fail(f"Source qualification log {name} SHA-256 does not match")
        paths[name] = path
    return paths


def validate_secret_report(path: Path, summary: dict) -> None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        fail(f"Source qualification raw secrets report is invalid: {error}")
    exact_keys(
        report,
        {"schema_version", "passed", "tracked_file_count", "private_secret_keys_checked", "findings"},
        "raw secrets report",
    )
    findings = exact_keys(
        report["findings"],
        {"exact_secret_matches", "suspicious_pattern_matches", "prohibited_tracked_files"},
        "raw secrets findings",
    )
    if type(report["schema_version"]) is not int or report["schema_version"] != 1 or report["passed"] is not True:
        fail("Source qualification raw secrets audit did not pass")
    if (
        type(report["tracked_file_count"]) is not int
        or report["tracked_file_count"] <= 0
        or type(report["private_secret_keys_checked"]) is not int
        or report["private_secret_keys_checked"] < 3
    ):
        fail("Source qualification raw secrets audit counters are invalid")
    if any(not isinstance(value, list) or value for value in findings.values()):
        fail("Source qualification raw secrets audit contains findings")
    expected = {
        "tracked_file_count": report["tracked_file_count"],
        "private_secret_keys_checked": report["private_secret_keys_checked"],
        "exact_secret_matches": len(findings["exact_secret_matches"]),
        "suspicious_pattern_matches": len(findings["suspicious_pattern_matches"]),
        "prohibited_tracked_files": len(findings["prohibited_tracked_files"]),
    }
    if summary != expected:
        fail("Source qualification secrets summary differs from raw audit")
    if any(type(value) is not int for value in summary.values()):
        fail("Source qualification did not compare at least three real private secrets")


def validate_ci_report(path: Path, ci: dict) -> None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        fail(f"Source qualification raw CI report is invalid: {error}")
    exact_keys(
        report,
        {"conclusion", "databaseId", "event", "headSha", "jobs", "name", "status", "url"},
        "raw CI report",
    )
    jobs = report["jobs"]
    if not isinstance(jobs, list):
        fail("Source qualification raw CI jobs are not a list")
    job = next(
        (
            item
            for item in jobs
            if isinstance(item, dict) and item.get("databaseId") == ci["job_id"]
        ),
        None,
    )
    if (
        report["databaseId"] != ci["run_id"]
        or report["headSha"] != ci["head_sha"]
        or report["conclusion"] != ci["conclusion"]
        or report["event"] != ci["event"]
        or report["url"] != ci["url"]
        or report["name"] != ci["workflow"]
        or report["status"] != "completed"
        or job is None
        or job.get("name") != "compile"
        or job.get("status") != "completed"
        or job.get("conclusion") != "success"
    ):
        fail("Source qualification raw CI report differs from reviewed metadata")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_source_commit: str | None = None,
    expected_size_bytes: int | None = None,
    expected_secrets_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    exact_keys(
        evidence,
        {"schema_version", "passed", "candidate", "reviewer", "reviewed_at", "logs", "ci", "build", "credentials", "secrets_audit"},
        "record",
    )
    if type(evidence["schema_version"]) is not int or evidence["schema_version"] != 2 or evidence["passed"] is not True:
        fail("Source qualification evidence did not pass with schema version 2")
    candidate = exact_keys(
        evidence["candidate"],
        {"project_version", "firmware_sha256", "source_commit"},
        "candidate",
    )
    version = require_text(candidate["project_version"], "candidate version")
    firmware_sha256 = require_text(candidate["firmware_sha256"], "candidate SHA-256", 64)
    source_commit = require_text(candidate["source_commit"], "candidate commit", 40)
    if re.fullmatch(r"[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+", version) is None:
        fail("Source qualification candidate version is invalid")
    if re.fullmatch(r"[0-9a-f]{64}", firmware_sha256) is None:
        fail("Source qualification firmware SHA-256 is invalid")
    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        fail("Source qualification source commit is invalid")
    if expected_version is not None and version != expected_version:
        fail("Source qualification version does not match")
    if expected_firmware_sha256 is not None and firmware_sha256 != expected_firmware_sha256:
        fail("Source qualification firmware SHA-256 does not match")
    if expected_source_commit is not None and source_commit != expected_source_commit:
        fail("Source qualification source commit does not match")
    require_text(evidence["reviewer"], "reviewer", 8)
    parse_reviewed_at(evidence["reviewed_at"])
    logs = resolve_logs(path, evidence["logs"])

    ci = exact_keys(
        evidence["ci"],
        {"repository", "workflow", "run_id", "job_id", "head_sha", "conclusion", "event", "url"},
        "ci",
    )
    if (
        ci["repository"] != "ProlificLab/esphomeLuxe"
        or ci["workflow"] != "Firmware source validation"
        or type(ci["run_id"]) is not int
        or ci["run_id"] <= 0
        or type(ci["job_id"]) is not int
        or ci["job_id"] <= 0
        or ci["head_sha"] != source_commit
        or ci["conclusion"] != "success"
        or ci["event"] not in {"pull_request", "push"}
        or ci["url"] != f"https://github.com/ProlificLab/esphomeLuxe/actions/runs/{ci['run_id']}"
    ):
        fail("Source qualification CI identity or conclusion is invalid")
    validate_ci_report(logs["ci"], ci)

    build = exact_keys(
        evidence["build"],
        {"count", "first_sha256", "second_sha256", "reproducible", "size_bytes", "partition_bytes", "usage_percent", "target_percent", "hard_percent", "hal6_baseline_bytes", "target_passed", "hard_limit_passed", "source_date_epoch", "container_image", "esp_idf"},
        "build",
    )
    size = build["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        fail("Source qualification firmware size is invalid")
    target_bytes = PARTITION_BYTES * TARGET_PERCENT // 100
    hard_bytes = PARTITION_BYTES * HARD_PERCENT // 100
    usage = size * 1000 // PARTITION_BYTES / 10
    source_date_epoch = build["source_date_epoch"]
    if (
        build["count"] != 2
        or build["first_sha256"] != firmware_sha256
        or build["second_sha256"] != firmware_sha256
        or build["reproducible"] is not True
        or build["partition_bytes"] != PARTITION_BYTES
        or build["usage_percent"] != usage
        or build["target_percent"] != TARGET_PERCENT
        or build["hard_percent"] != HARD_PERCENT
        or build["hal6_baseline_bytes"] != HAL6_BASELINE_BYTES
        or build["target_passed"] is not True
        or build["hard_limit_passed"] is not True
        or size > target_bytes
        or size > hard_bytes
        or size > HAL6_BASELINE_BYTES
        or type(source_date_epoch) is not int
        or source_date_epoch < 100000000
        or build["container_image"] != ESPHOME_IMAGE
        or build["esp_idf"] != "5.4.2"
    ):
        fail("Source qualification reproducibility or firmware budget did not pass")
    if expected_size_bytes is not None and size != expected_size_bytes:
        fail("Source qualification firmware size differs from the OTA artifact")
    for name in ("build_first", "build_second"):
        build_lines = logs[name].read_text(encoding="utf-8").splitlines()
        if firmware_sha256 not in "\n".join(build_lines):
            fail(f"Source qualification {name} log does not contain candidate SHA-256")
        if f"SOURCE_DATE_EPOCH={source_date_epoch}" not in build_lines:
            fail(f"Source qualification {name} log is not bound to commit build epoch")
    size_log = logs["firmware_size"].read_text(encoding="utf-8").splitlines()
    required_size_lines = {
        f"size_bytes={size}",
        f"partition_bytes={PARTITION_BYTES}",
        f"usage_percent={usage:.1f}",
        f"target_percent={TARGET_PERCENT}",
        f"hard_percent={HARD_PERCENT}",
        f"hal6_baseline_bytes={HAL6_BASELINE_BYTES}",
    }
    if not required_size_lines.issubset(size_log):
        fail("Source qualification firmware-size log differs from reviewed metrics")

    credentials = exact_keys(
        evidence["credentials"],
        {"file_sha256", "mounted_path", "read_only", "builds_bound"},
        "credentials",
    )
    secrets_sha256 = require_text(credentials["file_sha256"], "credentials SHA-256", 64)
    if (
        re.fullmatch(r"[0-9a-f]{64}", secrets_sha256) is None
        or credentials["mounted_path"] != "/config/secrets.yaml"
        or credentials["read_only"] is not True
        or credentials["builds_bound"] != 2
    ):
        fail("Source qualification credential build binding is invalid")
    if expected_secrets_sha256 is not None and secrets_sha256 != expected_secrets_sha256:
        fail("Source qualification credentials differ from the selected private file")
    marker = f"SECRETS SHA256={secrets_sha256}"
    for name in ("build_first", "build_second"):
        if marker not in logs[name].read_text(encoding="utf-8").splitlines():
            fail(f"Source qualification {name} log is not bound to selected credentials")

    summary = exact_keys(
        evidence["secrets_audit"],
        {"tracked_file_count", "private_secret_keys_checked", "exact_secret_matches", "suspicious_pattern_matches", "prohibited_tracked_files"},
        "secrets_audit",
    )
    validate_secret_report(logs["secrets_audit"], summary)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-source-commit")
    parser.add_argument("--expected-size-bytes", type=int)
    parser.add_argument("--expected-secrets-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_source_commit,
        args.expected_size_bytes,
        args.expected_secrets_sha256,
    )
    print(
        "Source qualification evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"ci_run={evidence['ci']['run_id']} size={evidence['build']['size_bytes']}."
    )


if __name__ == "__main__":
    main()
