#!/usr/bin/env python3
"""Validate human-observed Muse Luxe physical control evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


OBSERVATIONS = {
    "continuous_timeout",
    "double_press_stop",
    "listening_led_visible",
    "long_press_privacy",
    "privacy_led_visible",
    "single_press_mute",
    "triple_press_continuous_start",
    "triple_press_continuous_stop",
    "volume_down",
    "volume_up",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Physical controls {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Physical controls {label} is still a placeholder")
    return text


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Physical controls observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Physical controls observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Physical controls observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Physical controls evidence is older than 30 days")
    return observed_utc


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "location",
        "observations",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Physical controls evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Physical controls evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    if not isinstance(candidate, dict) or set(candidate) != {
        "device_name",
        "hardware",
        "project_version",
        "firmware_sha256",
    }:
        fail("Physical controls candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    require_text(candidate["hardware"], "candidate hardware")
    version = require_text(candidate["project_version"], "candidate project_version")
    digest = require_text(
        candidate["firmware_sha256"], "candidate firmware_sha256", minimum=64
    )
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail("Physical controls firmware_sha256 is not a lowercase SHA-256")
    if expected_version is not None and version != expected_version:
        fail("Physical controls firmware version does not match")
    if expected_firmware_sha256 is not None and digest != expected_firmware_sha256:
        fail("Physical controls firmware SHA-256 does not match")

    require_text(evidence["observer"], "observer")
    require_text(evidence["location"], "location", minimum=3)
    parse_observed_at(evidence["observed_at"])

    observations = evidence["observations"]
    if not isinstance(observations, dict) or set(observations) != OBSERVATIONS:
        fail("Physical controls observations differ from the closed checklist")
    for name, observation in observations.items():
        if not isinstance(observation, dict) or set(observation) != {
            "passed",
            "evidence",
        }:
            fail(f"Physical controls observation {name} keys differ from schema")
        if observation["passed"] is not True:
            fail(f"Physical controls observation {name} did not pass")
        require_text(observation["evidence"], f"observation {name} evidence")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
    )
    print(
        "Physical controls evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"observations={len(evidence['observations'])}."
    )


if __name__ == "__main__":
    main()
