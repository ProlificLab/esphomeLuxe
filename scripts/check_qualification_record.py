#!/usr/bin/env python3
"""Validate release qualification evidence against the exact OTA artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_endurance_summary import validate_summary


BETA_GATES = {
    "build_reproducible",
    "canary_ota",
    "ci_passed",
    "firmware_size_hard_limit",
    "ha_restart_recovery_10",
    "physical_controls",
    "privacy_reboot",
    "reboot_recovery_10",
    "rollback_artifact_verified",
    "secrets_audit",
    "tts_cycles_100",
    "wifi_recovery_10",
}

STABLE_GATES = BETA_GATES | {
    "access_sensor_routines",
    "acoustic_calibration",
    "camera_alerts_deduplicated",
    "emergency_offline",
    "firmware_size_target",
    "idle_endurance_24h",
    "intercom_two_satellite",
    "interpreter_bilingual",
    "music_transfer_two_satellite",
    "offline_rescue_physical",
    "rollback_exercised",
    "second_person_install",
}

TOP_LEVEL_KEYS = {
    "schema_version",
    "channel",
    "version",
    "source_commit",
    "firmware_sha256",
    "reviewer",
    "reviewed_at",
    "canary_device",
    "compatibility",
    "feature_scope",
    "open_gates",
    "gates",
}

COMPATIBILITY_KEYS = {
    "hardware",
    "home_assistant",
    "esphome",
    "esp_idf",
}

PLACEHOLDERS = {"", "none", "pending", "todo", "tbd", "unknown", "n/a"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 3) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Qualification {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"Qualification {label} is still a placeholder")
    return text


def parse_review_time(value: object) -> datetime:
    text = require_text(value, "reviewed_at")
    try:
        reviewed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Qualification reviewed_at is not ISO-8601: {error}")
    if reviewed.tzinfo is None:
        fail("Qualification reviewed_at must include a timezone")
    now = datetime.now(timezone.utc)
    reviewed_utc = reviewed.astimezone(timezone.utc)
    if reviewed_utc > now + timedelta(minutes=5):
        fail("Qualification reviewed_at is in the future")
    if reviewed_utc < now - timedelta(days=30):
        fail("Qualification record is older than 30 days")
    return reviewed_utc


def validate_gate(name: str, value: object) -> str:
    if not isinstance(value, dict) or set(value) != {"passed", "evidence"}:
        fail(f"Gate {name} must contain exactly passed and evidence")
    if value["passed"] is not True:
        fail(f"Gate {name} has not passed")
    evidence = require_text(value["evidence"], f"gate {name} evidence", minimum=8)
    lowered = evidence.lower()
    if any(marker in lowered for marker in ("pending", "todo", "tbd")):
        fail(f"Gate {name} evidence is not final")
    return evidence


def current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--channel", required=True, choices=("beta", "stable"))
    parser.add_argument("--source-commit", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    record = json.loads(args.record.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or set(record) != TOP_LEVEL_KEYS:
        fail(
            "Qualification record keys differ from schema: "
            f"expected={sorted(TOP_LEVEL_KEYS)} actual={sorted(record) if isinstance(record, dict) else type(record).__name__}"
        )
    if record["schema_version"] != 1:
        fail("Unsupported qualification schema version")
    if record["channel"] != args.channel:
        fail("Qualification channel does not match requested promotion")

    version = manifest.get("version")
    if record["version"] != version:
        fail("Qualification version does not match manifest")
    if manifest.get("channel") != args.channel:
        fail("Manifest channel does not match requested promotion")
    if args.channel == "stable" and re.search(r"(?:alpha|beta|rc)", version or "", re.I):
        fail("A prerelease version cannot be qualified as stable")

    expected_commit = args.source_commit or current_commit()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        fail("Expected source commit is not a full lowercase Git SHA")
    if record["source_commit"] != expected_commit:
        fail("Qualification source commit does not match promoted source")

    artifact_hash = sha256(args.artifact)
    if record["firmware_sha256"] != artifact_hash:
        fail("Qualification SHA-256 does not match OTA artifact")
    require_text(record["reviewer"], "reviewer")
    require_text(record["canary_device"], "canary_device")
    parse_review_time(record["reviewed_at"])

    compatibility = record["compatibility"]
    if not isinstance(compatibility, dict) or set(compatibility) != COMPATIBILITY_KEYS:
        fail("Qualification compatibility matrix is incomplete or has unknown keys")
    for key, value in compatibility.items():
        require_text(value, f"compatibility {key}")

    feature_scope = record["feature_scope"]
    if not isinstance(feature_scope, list) or not feature_scope:
        fail("Qualification feature_scope must be a non-empty list")
    for index, value in enumerate(feature_scope):
        require_text(value, f"feature_scope[{index}]")

    open_gates = record["open_gates"]
    if not isinstance(open_gates, list):
        fail("Qualification open_gates must be a list")
    if args.channel == "stable" and open_gates:
        fail("Stable qualification cannot retain open gates")
    for index, value in enumerate(open_gates):
        require_text(value, f"open_gates[{index}]")

    gates = record["gates"]
    if not isinstance(gates, dict):
        fail("Qualification gates must be an object")
    unknown_gates = set(gates) - STABLE_GATES
    if unknown_gates:
        fail(f"Unknown qualification gates: {sorted(unknown_gates)}")
    required_gates = STABLE_GATES if args.channel == "stable" else BETA_GATES
    missing_gates = required_gates - set(gates)
    if missing_gates:
        fail(f"Missing qualification gates: {sorted(missing_gates)}")
    gate_evidence = {
        name: validate_gate(name, gates[name]) for name in sorted(required_gates)
    }
    if args.channel == "stable":
        match = re.fullmatch(
            r"sha256:([0-9a-f]{64})\s+(.+)",
            gate_evidence["idle_endurance_24h"],
        )
        if match is None:
            fail("Endurance evidence must contain its SHA-256 and relative path")
        expected_evidence_hash, evidence_name = match.groups()
        evidence_path = Path(evidence_name)
        if evidence_path.is_absolute() or ".." in evidence_path.parts:
            fail("Endurance evidence must be a safe path relative to the record")
        evidence_root = args.record.parent.resolve()
        resolved_evidence = (evidence_root / evidence_path).resolve()
        if not resolved_evidence.is_relative_to(evidence_root):
            fail("Endurance evidence resolves outside the qualification directory")
        if sha256(resolved_evidence) != expected_evidence_hash:
            fail("Endurance evidence SHA-256 does not match the reviewed record")
        validate_summary(resolved_evidence, version)

    print(
        f"Qualification passed for {args.channel} {version}: "
        f"commit={expected_commit[:12]} sha256={artifact_hash[:16]} "
        f"gates={len(required_gates)}."
    )


if __name__ == "__main__":
    main()
