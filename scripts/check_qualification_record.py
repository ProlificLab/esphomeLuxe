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
from check_hal9_modes_evidence import validate_evidence as validate_modes_evidence
from check_night_led_evidence import validate_evidence as validate_night_led_evidence
from check_offline_rescue_evidence import (
    validate_evidence as validate_offline_rescue_evidence,
)
from check_physical_controls_evidence import (
    validate_evidence as validate_physical_controls_evidence,
)
from check_timer_evidence import validate_evidence as validate_timer_evidence


BETA_GATES = {
    "build_reproducible",
    "canary_ota",
    "ci_passed",
    "firmware_size_hard_limit",
    "ha_restart_recovery_10",
    "mode_api_transitions",
    "physical_controls",
    "privacy_reboot",
    "reboot_recovery_10",
    "rollback_artifact_verified",
    "secrets_audit",
    "tts_cycles_100",
    "wifi_recovery_10",
}

ROADMAP_FEATURE_GATES = {
    "access_sensor_routines",
    "acoustic_guardian_physical",
    "acoustic_calibration",
    "announcement_routing_queue",
    "camera_alerts_deduplicated",
    "emergency_offline",
    "family_message_delivery",
    "house_intelligence_freshness",
    "interactive_routine_handoff",
    "intercom_two_satellite",
    "interpreter_bilingual",
    "music_transfer_two_satellite",
    "night_led_profiles",
    "offline_rescue_physical",
    "timer_multi_pause_reconnect",
    "video_review_authenticated",
}

STABLE_GATES = BETA_GATES | ROADMAP_FEATURE_GATES | {
    "firmware_size_target",
    "idle_endurance_24h",
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


def resolve_bound_evidence(record_path: Path, evidence: str, label: str) -> Path:
    match = re.fullmatch(r"sha256:([0-9a-f]{64})\s+(.+)", evidence)
    if match is None:
        fail(f"{label} evidence must contain its SHA-256 and relative path")
    expected_hash, evidence_name = match.groups()
    relative_path = Path(evidence_name)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        fail(f"{label} evidence must be a safe path relative to the record")
    evidence_root = record_path.parent.resolve()
    resolved = (evidence_root / relative_path).resolve()
    if not resolved.is_relative_to(evidence_root):
        fail(f"{label} evidence resolves outside the qualification directory")
    if not resolved.is_file():
        fail(f"{label} evidence file does not exist")
    if sha256(resolved) != expected_hash:
        fail(f"{label} evidence SHA-256 does not match the reviewed record")
    return resolved


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
    modes_path = resolve_bound_evidence(
        args.record,
        gate_evidence["mode_api_transitions"],
        "Modes",
    )
    validate_modes_evidence(modes_path, version)
    physical_controls_path = resolve_bound_evidence(
        args.record,
        gate_evidence["physical_controls"],
        "Physical controls",
    )
    validate_physical_controls_evidence(
        physical_controls_path,
        version,
        artifact_hash,
    )
    if args.channel == "stable":
        if gate_evidence["emergency_offline"] != gate_evidence["offline_rescue_physical"]:
            fail("Offline rescue stable gates must bind the same evidence record")
        package_path = (
            Path(__file__).resolve().parents[1]
            / "home-assistant/packages/muse_luxe.yaml"
        )
        night_led_path = resolve_bound_evidence(
            args.record,
            gate_evidence["night_led_profiles"],
            "Night LED",
        )
        validate_night_led_evidence(
            night_led_path,
            version,
            artifact_hash,
            sha256(package_path),
        )
        timer_package_path = (
            Path(__file__).resolve().parents[1]
            / "home-assistant/packages/muse_timer_coach.yaml"
        )
        timer_path = resolve_bound_evidence(
            args.record,
            gate_evidence["timer_multi_pause_reconnect"],
            "Timer",
        )
        validate_timer_evidence(
            timer_path,
            version,
            artifact_hash,
            sha256(package_path),
            sha256(timer_package_path),
        )
        rescue_path = resolve_bound_evidence(
            args.record,
            gate_evidence["offline_rescue_physical"],
            "Offline rescue",
        )
        root = Path(__file__).resolve().parents[1]
        validate_offline_rescue_evidence(
            rescue_path,
            version,
            artifact_hash,
            sha256(root / "packages/offline_rescue.yaml"),
            sha256(root / "components/offline_media/offline_media.cpp"),
        )
        endurance_path = resolve_bound_evidence(
            args.record,
            gate_evidence["idle_endurance_24h"],
            "Endurance",
        )
        validate_summary(endurance_path, version)

    print(
        f"Qualification passed for {args.channel} {version}: "
        f"commit={expected_commit[:12]} sha256={artifact_hash[:16]} "
        f"gates={len(required_gates)}."
    )


if __name__ == "__main__":
    main()
