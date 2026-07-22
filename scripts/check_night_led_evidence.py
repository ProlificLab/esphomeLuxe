#!/usr/bin/env python3
"""Validate candidate-bound day/night LED qualification evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


PROFILES = {
    "answering": (100, 20),
    "error": (100, 35),
    "listening": (100, 25),
    "offline": (45, 15),
    "playing": (60, 10),
    "privacy": (35, 20),
    "rescue": (80, 35),
    "starting": (40, 15),
    "waiting": (100, 10),
}
SCENARIOS = {
    "ha_disconnect_during_timer",
    "listening_visible_at_night",
    "privacy_visible_at_night",
    "rescue_visible_at_night",
    "timer_day_night_transition",
    "waiting_api_day_night_restore",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Night LED {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Night LED {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Night LED {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Night LED observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Night LED observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Night LED observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Night LED evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Night LED {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Night LED {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_ha_package_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "profiles",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Night LED evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Night LED evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    if not isinstance(candidate, dict) or set(candidate) != {
        "device_name",
        "project_version",
        "firmware_sha256",
        "ha_package_sha256",
    }:
        fail("Night LED candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(
        candidate["ha_package_sha256"], "ha_package_sha256"
    )
    if expected_version is not None and version != expected_version:
        fail("Night LED firmware version does not match")
    if (
        expected_firmware_sha256 is not None
        and firmware_digest != expected_firmware_sha256
    ):
        fail("Night LED firmware SHA-256 does not match")
    if (
        expected_ha_package_sha256 is not None
        and package_digest != expected_ha_package_sha256
    ):
        fail("Night LED HA package SHA-256 does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    profiles = evidence["profiles"]
    if not isinstance(profiles, dict) or set(profiles) != set(PROFILES):
        fail("Night LED profiles differ from the closed phase table")
    for name, expected in PROFILES.items():
        profile = profiles[name]
        if not isinstance(profile, dict) or set(profile) != {
            "passed",
            "day_brightness_pct",
            "night_brightness_pct",
            "evidence",
        }:
            fail(f"Night LED profile {name} keys differ from schema")
        if profile["passed"] is not True:
            fail(f"Night LED profile {name} did not pass")
        actual = (profile["day_brightness_pct"], profile["night_brightness_pct"])
        if actual != expected:
            fail(f"Night LED profile {name} brightness differs from policy")
        require_text(profile["evidence"], f"profile {name} evidence")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Night LED scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-ha-package-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_ha_package_sha256,
    )
    print(
        "Night LED evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"profiles={len(evidence['profiles'])} scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
