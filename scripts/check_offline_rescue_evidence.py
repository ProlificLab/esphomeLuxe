#!/usr/bin/env python3
"""Validate candidate-bound physical offline-rescue evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


CLIPS = {
    "ALLCLEAR.WAV",
    "EVAC.WAV",
    "EVACLIST.WAV",
    "POWER.WAV",
    "PWRLIST.WAV",
    "READY.WAV",
}
SCENARIOS = {
    "all_six_files_play",
    "card_insert_after_boot_mounts",
    "card_manifest_unchanged_after_test",
    "card_ready_diagnostic",
    "enter_quadruple_press",
    "evacuation_triple_press",
    "exit_quadruple_press_to_waiting",
    "fixed_sequence_wraps",
    "ha_loss_playback_continues",
    "ha_reconnect_does_not_exit",
    "missing_card_error_visible",
    "privacy_stops_and_blocks_entry",
    "reboot_restores_rescue",
    "stop_double_press",
    "volume_buttons_during_playback",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Offline rescue {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Offline rescue {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Offline rescue {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Offline rescue observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Offline rescue observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Offline rescue observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Offline rescue evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Offline rescue {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Offline rescue {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_component_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "card",
        "metrics",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Offline rescue evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Offline rescue evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "rescue_package_sha256",
        "offline_component_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Offline rescue candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(
        candidate["rescue_package_sha256"], "rescue_package_sha256"
    )
    component_digest = require_digest(
        candidate["offline_component_sha256"], "offline_component_sha256"
    )
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (package_digest, expected_package_sha256, "rescue package SHA-256"),
        (component_digest, expected_component_sha256, "component SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Offline rescue {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    card = evidence["card"]
    if not isinstance(card, dict) or set(card) != {
        "volume_label",
        "manifest_sha256_before",
        "manifest_sha256_after",
        "files",
    }:
        fail("Offline rescue card identity differs from schema")
    if card["volume_label"] != "MUSE_RESCUE":
        fail("Offline rescue card volume label differs from policy")
    before = require_digest(card["manifest_sha256_before"], "card manifest before")
    after = require_digest(card["manifest_sha256_after"], "card manifest after")
    if before != after:
        fail("Offline rescue card manifest changed during firmware tests")
    if not isinstance(card["files"], list) or set(card["files"]) != CLIPS:
        fail("Offline rescue card files differ from the fixed allowlist")
    if len(card["files"]) != len(CLIPS):
        fail("Offline rescue card contains duplicate allowlisted files")

    metrics = evidence["metrics"]
    metric_keys = {
        "clip_play_counts",
        "ha_disconnect_cycles",
        "ha_reconnect_cycles",
        "reboots_while_rescue",
        "unexpected_media_errors",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Offline rescue metrics differ from schema")
    play_counts = metrics["clip_play_counts"]
    if not isinstance(play_counts, dict) or set(play_counts) != CLIPS:
        fail("Offline rescue clip counts differ from the fixed allowlist")
    if any(
        not isinstance(count, int) or isinstance(count, bool) or count < 1
        for count in play_counts.values()
    ):
        fail("Offline rescue every fixed clip must be heard at least once")
    for metric in ("ha_disconnect_cycles", "ha_reconnect_cycles", "reboots_while_rescue"):
        if type(metrics[metric]) is not int or metrics[metric] != 1:
            fail(f"Offline rescue {metric} must equal one")
    if (
        type(metrics["unexpected_media_errors"]) is not int
        or metrics["unexpected_media_errors"] != 0
    ):
        fail("Offline rescue reported unexpected media errors")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Offline rescue scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-component-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_component_sha256,
    )
    print(
        "Offline rescue evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
