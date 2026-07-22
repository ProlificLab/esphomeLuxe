#!/usr/bin/env python3
"""Validate candidate-bound physical authenticated-video-review evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


CAMERA_MAP = {
    "avant_jardin": "image.avant_jardin_person",
    "sonnette": "image.sonnette_person",
}
SCENARIOS = {
    "below_threshold_rejected",
    "event_id_and_camera_match_frigate",
    "fresh_avant_jardin_opens_correct_card",
    "fresh_sonnette_opens_correct_card",
    "ha_restart_resets_private_state",
    "non_person_event_ignored",
    "no_mobile_or_external_delivery",
    "no_public_url_or_token",
    "review_requires_ha_authentication",
    "stale_image_rejected",
    "unmapped_camera_rejected",
    "window_expiry_hides_card",
    "window_expiry_removes_notice",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Video review {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Video review {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Video review {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Video review observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Video review observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Video review observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Video review evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Video review {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Video review {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_dashboard_sha256: str | None = None,
    expected_provisioner_sha256: str | None = None,
) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "passed",
        "candidate",
        "observer",
        "observed_at",
        "runtime",
        "metrics",
        "final_state",
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Video review evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Video review evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "ha_package_sha256",
        "dashboard_sha256",
        "provisioner_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Video review candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(candidate["ha_package_sha256"], "package SHA-256")
    dashboard_digest = require_digest(candidate["dashboard_sha256"], "dashboard SHA-256")
    provisioner_digest = require_digest(
        candidate["provisioner_sha256"], "provisioner SHA-256"
    )
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (package_digest, expected_package_sha256, "package SHA-256"),
        (dashboard_digest, expected_dashboard_sha256, "dashboard SHA-256"),
        (provisioner_digest, expected_provisioner_sha256, "provisioner SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Video review {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {
        "camera_map",
        "destination",
        "authenticated_frontend",
        "window_seconds",
        "maximum_image_age_seconds",
        "maximum_image_before_event_seconds",
    }:
        fail("Video review runtime differs from schema")
    if runtime["camera_map"] != CAMERA_MAP:
        fail("Video review camera map differs from the closed map")
    if runtime["destination"] != "ha_dashboard":
        fail("Video review destination is not the authenticated HA dashboard")
    if runtime["authenticated_frontend"] is not True:
        fail("Video review frontend authentication was not verified")
    exact_runtime = {
        "window_seconds": 300,
        "maximum_image_age_seconds": 30,
        "maximum_image_before_event_seconds": 5,
    }
    for name, expected_value in exact_runtime.items():
        if type(runtime[name]) is not int or runtime[name] != expected_value:
            fail(f"Video review {name} differs from policy")

    metrics = evidence["metrics"]
    metric_keys = {
        "accepted_events",
        "below_threshold_rejections",
        "unmapped_camera_rejections",
        "non_person_rejections",
        "stale_image_rejections",
        "expired_windows",
        "ha_restart_cycles",
        "public_urls_or_tokens",
        "external_deliveries",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Video review metrics differ from schema")
    accepted = metrics["accepted_events"]
    if not isinstance(accepted, dict) or set(accepted) != set(CAMERA_MAP):
        fail("Video review accepted-event cameras differ from the closed map")
    if any(type(count) is not int or count < 1 for count in accepted.values()):
        fail("Video review needs one accepted event for each camera")
    for name in (
        "below_threshold_rejections",
        "unmapped_camera_rejections",
        "non_person_rejections",
        "stale_image_rejections",
    ):
        if type(metrics[name]) is not int or metrics[name] < 1:
            fail(f"Video review {name} was not exercised")
    if type(metrics["expired_windows"]) is not int or metrics["expired_windows"] < 2:
        fail("Video review expiry was not exercised for both cameras")
    if type(metrics["ha_restart_cycles"]) is not int or metrics["ha_restart_cycles"] != 1:
        fail("Video review must include exactly one HA restart cycle")
    for name in ("public_urls_or_tokens", "external_deliveries"):
        if type(metrics[name]) is not int or metrics[name] != 0:
            fail(f"Video review {name} must remain zero")

    final_state = evidence["final_state"]
    if not isinstance(final_state, dict) or final_state != {
        "enabled": False,
        "destination": "disabled",
        "camera": "none",
        "window_active": False,
    }:
        fail("Video review final private state is not closed")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Video review scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-dashboard-sha256")
    parser.add_argument("--expected-provisioner-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_dashboard_sha256,
        args.expected_provisioner_sha256,
    )
    print(
        "Video review evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
