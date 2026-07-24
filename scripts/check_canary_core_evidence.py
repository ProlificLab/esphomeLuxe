#!/usr/bin/env python3
"""Validate the single physical evidence record for core canary gates."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re


TEST_NAMES = {
    "canary_ota",
    "ha_restart_recovery",
    "privacy_reboot",
    "reboot_recovery",
    "rollback_artifact",
    "tts_cycles",
    "wifi_recovery",
}
RECOVERY_TESTS = {
    "ha_restart_recovery": (10, "max_ha_recovery_seconds"),
    "reboot_recovery": (10, "max_reboot_recovery_seconds"),
    "wifi_recovery": (10, "max_wifi_recovery_seconds"),
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 3) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Canary core {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Canary core {label} is still a placeholder")
    return text


def parse_time(value: object, label: str) -> datetime:
    text = require_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Canary core {label} is invalid: {error}")
    if parsed.tzinfo is None:
        fail(f"Canary core {label} must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if parsed > now + timedelta(minutes=5):
        fail(f"Canary core {label} is in the future")
    if parsed < now - timedelta(days=30):
        fail(f"Canary core {label} is older than 30 days")
    return parsed


def require_exact_keys(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"Canary core {label} keys differ from schema")
    return value


def require_final_health(test: dict, label: str) -> None:
    if (
        test["final_state"] != "waiting"
        or test["final_health"] != "healthy"
        or test["final_error"] != ""
    ):
        fail(f"Canary core {label} did not finish waiting, healthy and error-free")


def validate_logs(record_path: Path, value: object) -> None:
    logs = require_exact_keys(value, TEST_NAMES, "logs")
    evidence_root = record_path.parent.resolve()
    resolved_logs: set[Path] = set()
    for name, binding in logs.items():
        if not isinstance(binding, str):
            fail(f"Canary core log {name} binding is not text")
        match = re.fullmatch(r"sha256:([0-9a-f]{64})\s+(.+)", binding)
        if match is None:
            fail(f"Canary core log {name} is not hash-bound")
        expected_hash, relative_name = match.groups()
        relative_path = Path(relative_name)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            fail(f"Canary core log {name} path is unsafe")
        resolved = (evidence_root / relative_path).resolve()
        if (
            not resolved.is_relative_to(evidence_root)
            or not resolved.is_file()
            or resolved.stat().st_size == 0
        ):
            fail(f"Canary core log {name} does not exist in the evidence directory")
        if resolved in resolved_logs:
            fail("Canary core tests must bind seven distinct raw logs")
        resolved_logs.add(resolved)
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if digest != expected_hash:
            fail(f"Canary core log {name} SHA-256 does not match")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_source_commit: str | None = None,
    expected_device: str | None = None,
    expected_rollback_md5: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    require_exact_keys(
        evidence,
        {
            "schema_version",
            "passed",
            "candidate",
            "observer",
            "started_at",
            "finished_at",
            "limits",
            "logs",
            "tests",
        },
        "record",
    )
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Canary core evidence did not pass with schema version 1")

    candidate = require_exact_keys(
        evidence["candidate"],
        {
            "device_name",
            "hardware",
            "project_version",
            "firmware_sha256",
            "source_commit",
        },
        "candidate",
    )
    device = require_text(candidate["device_name"], "candidate device_name")
    require_text(candidate["hardware"], "candidate hardware", minimum=8)
    version = require_text(candidate["project_version"], "candidate project_version")
    firmware_sha256 = require_text(
        candidate["firmware_sha256"], "candidate firmware_sha256", minimum=64
    )
    source_commit = require_text(
        candidate["source_commit"], "candidate source_commit", minimum=40
    )
    if re.fullmatch(r"[0-9a-f]{64}", firmware_sha256) is None:
        fail("Canary core firmware_sha256 is not a lowercase SHA-256")
    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        fail("Canary core source_commit is not a full lowercase Git SHA")
    if expected_version is not None and version != expected_version:
        fail("Canary core firmware version does not match")
    if expected_firmware_sha256 is not None and firmware_sha256 != expected_firmware_sha256:
        fail("Canary core firmware SHA-256 does not match")
    if expected_source_commit is not None and source_commit != expected_source_commit:
        fail("Canary core source commit does not match")
    if expected_device is not None and device != expected_device:
        fail("Canary core device does not match qualification record")

    require_text(evidence["observer"], "observer", minimum=8)
    started = parse_time(evidence["started_at"], "started_at")
    finished = parse_time(evidence["finished_at"], "finished_at")
    if finished < started:
        fail("Canary core finished_at precedes started_at")

    limits = require_exact_keys(
        evidence["limits"],
        {
            "max_wifi_recovery_seconds",
            "max_ha_recovery_seconds",
            "max_reboot_recovery_seconds",
        },
        "limits",
    )
    if limits != {
        "max_wifi_recovery_seconds": 10,
        "max_ha_recovery_seconds": 10,
        "max_reboot_recovery_seconds": 20,
    }:
        fail("Canary core recovery limits differ from the release contract")

    validate_logs(path, evidence["logs"])

    tests = require_exact_keys(evidence["tests"], TEST_NAMES, "tests")
    ota = require_exact_keys(
        tests["canary_ota"],
        {
            "attempted",
            "completed",
            "installed_sha256_match",
            "exact_version",
            "final_state",
            "final_health",
            "final_error",
            "manual_interventions",
        },
        "canary_ota",
    )
    if (
        ota["attempted"] != 1
        or ota["completed"] != 1
        or ota["installed_sha256_match"] is not True
        or ota["exact_version"] is not True
        or ota["manual_interventions"] != 0
    ):
        fail("Canary core exact OTA installation did not pass once without intervention")
    require_final_health(ota, "canary_ota")

    recovery_keys = {
        "attempted",
        "completed",
        "max_recovery_seconds",
        "manual_interventions",
        "final_state",
        "final_health",
        "final_error",
    }
    for name, (required_count, limit_name) in RECOVERY_TESTS.items():
        test = require_exact_keys(tests[name], recovery_keys, name)
        duration = test["max_recovery_seconds"]
        if (
            test["attempted"] != required_count
            or test["completed"] != required_count
            or test["manual_interventions"] != 0
            or isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or duration < 0
            or duration >= limits[limit_name]
        ):
            fail(f"Canary core {name} counts or recovery limit did not pass")
        require_final_health(test, name)

    privacy = require_exact_keys(
        tests["privacy_reboot"],
        {"persisted", "cleared", "final_state", "final_health", "final_error"},
        "privacy_reboot",
    )
    if privacy["persisted"] is not True or privacy["cleared"] is not True:
        fail("Canary core privacy did not persist and clear across reboot")
    require_final_health(privacy, "privacy_reboot")

    tts = require_exact_keys(
        tests["tts_cycles"],
        {
            "requested",
            "completed",
            "heard",
            "failures",
            "ring_buffer_resets",
            "voice_errors",
            "final_state",
            "final_health",
            "final_error",
        },
        "tts_cycles",
    )
    if (
        tts["requested"] != 100
        or tts["completed"] != 100
        or tts["heard"] != 100
        or tts["failures"] != 0
        or tts["ring_buffer_resets"] != 0
        or tts["voice_errors"] != 0
    ):
        fail("Canary core 100 TTS cycles did not complete audibly without errors")
    require_final_health(tts, "tts_cycles")

    rollback = require_exact_keys(
        tests["rollback_artifact"],
        {"version", "sha256", "md5", "size_bytes", "stored_offline", "verified"},
        "rollback_artifact",
    )
    if (
        rollback["version"] != "2025.3.1-hal.6"
        or re.fullmatch(r"[0-9a-f]{64}", str(rollback["sha256"])) is None
        or re.fullmatch(r"[0-9a-f]{32}", str(rollback["md5"])) is None
        or isinstance(rollback["size_bytes"], bool)
        or not isinstance(rollback["size_bytes"], int)
        or rollback["size_bytes"] <= 0
        or rollback["stored_offline"] is not True
        or rollback["verified"] is not True
    ):
        fail("Canary core hal.6 rollback artifact is not retained and verified")
    if expected_rollback_md5 is not None and rollback["md5"] != expected_rollback_md5:
        fail("Canary core rollback MD5 differs from the immutable hal.6 manifest")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-source-commit")
    parser.add_argument("--expected-device")
    parser.add_argument("--expected-rollback-md5")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_source_commit,
        args.expected_device,
        args.expected_rollback_md5,
    )
    print(
        "Canary core evidence passed: "
        f"version={evidence['candidate']['project_version']} tests={len(TEST_NAMES)}."
    )


if __name__ == "__main__":
    main()
