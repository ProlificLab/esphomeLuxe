#!/usr/bin/env python3
"""Validate candidate-bound physical house-intelligence evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


DOMAINS = ["frigate", "opnsense", "proxmox", "victron"]
THRESHOLDS = {
    "frigate_seconds": 30,
    "opnsense_seconds": 120,
    "proxmox_seconds": 300,
    "victron_seconds": 300,
}
ROLES = {
    "frigate": "viewer",
    "opnsense": "page-muse-readonly",
    "proxmox": "PVEAuditor",
    "victron": "read-only entities",
}
SCENARIOS = {
    "assist_exposes_normalized_facts_only",
    "combined_fresh_narration",
    "frigate_fresh_camera_counts",
    "frigate_oldest_sentinel_wins",
    "frigate_recovers_after_fresh_data",
    "frigate_stale_refuses_values",
    "frigate_viewer_controls_disabled",
    "narration_uses_deterministic_template",
    "opnsense_forbidden_api_returns_403",
    "opnsense_fresh_multiwan",
    "opnsense_get_succeeds",
    "opnsense_post_returns_405",
    "opnsense_recovers_after_fresh_data",
    "opnsense_stale_refuses_values",
    "proxmox_fresh_values",
    "proxmox_oldest_required_source_wins",
    "proxmox_pveauditor_only",
    "proxmox_recovers_after_fresh_data",
    "proxmox_stale_refuses_values",
    "victron_fresh_values",
    "victron_oldest_required_source_wins",
    "victron_recovers_after_fresh_data",
    "victron_stale_refuses_values",
}
PLACEHOLDERS = {"pending", "todo", "tbd", "replace", "unknown", "not tested"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"House intelligence {label} is missing or too short")
    text = value.strip()
    if text.lower() in PLACEHOLDERS:
        fail(f"House intelligence {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        fail(f"House intelligence {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"House intelligence observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("House intelligence observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed = observed.astimezone(timezone.utc)
    if observed > now + timedelta(minutes=5):
        fail("House intelligence observed_at is in the future")
    if observed < now - timedelta(days=30):
        fail("House intelligence evidence is older than 30 days")
    return observed


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"House intelligence {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"House intelligence {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_opnsense_controller_sha256: str | None = None,
    expected_opnsense_acl_sha256: str | None = None,
    expected_proxmox_policy_sha256: str | None = None,
    expected_frigate_policy_sha256: str | None = None,
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
        fail("House intelligence evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("House intelligence evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "ha_package_sha256",
        "opnsense_controller_sha256",
        "opnsense_acl_sha256",
        "proxmox_policy_sha256",
        "frigate_policy_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("House intelligence candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    actual = {
        "firmware SHA-256": require_digest(
            candidate["firmware_sha256"], "firmware_sha256"
        ),
        "HA package SHA-256": require_digest(
            candidate["ha_package_sha256"], "ha_package_sha256"
        ),
        "OPNsense controller SHA-256": require_digest(
            candidate["opnsense_controller_sha256"], "opnsense_controller_sha256"
        ),
        "OPNsense ACL SHA-256": require_digest(
            candidate["opnsense_acl_sha256"], "opnsense_acl_sha256"
        ),
        "Proxmox policy SHA-256": require_digest(
            candidate["proxmox_policy_sha256"], "proxmox_policy_sha256"
        ),
        "Frigate policy SHA-256": require_digest(
            candidate["frigate_policy_sha256"], "frigate_policy_sha256"
        ),
    }
    expected = {
        "firmware SHA-256": expected_firmware_sha256,
        "HA package SHA-256": expected_package_sha256,
        "OPNsense controller SHA-256": expected_opnsense_controller_sha256,
        "OPNsense ACL SHA-256": expected_opnsense_acl_sha256,
        "Proxmox policy SHA-256": expected_proxmox_policy_sha256,
        "Frigate policy SHA-256": expected_frigate_policy_sha256,
    }
    if expected_version is not None and version != expected_version:
        fail("House intelligence firmware version does not match")
    for label, wanted in expected.items():
        if wanted is not None and actual[label] != wanted:
            fail(f"House intelligence {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or runtime != {
        "domains": DOMAINS,
        "stale_thresholds": THRESHOLDS,
        "credential_roles": ROLES,
        "narration_target": "media_player.raspiaudio_muse_luxe",
    }:
        fail("House intelligence runtime differs from the closed contract")

    metrics = evidence["metrics"]
    metric_keys = {
        "successful_narrations",
        "fresh_domain_checks",
        "stale_domain_checks",
        "recovery_checks",
        "oldest_source_checks",
        "opnsense_denied_writes",
        "max_narration_latency_seconds",
        "infrastructure_actions",
        "external_deliveries",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("House intelligence metrics differ from schema")
    minimums = {
        "successful_narrations": 5,
        "fresh_domain_checks": 4,
        "stale_domain_checks": 4,
        "recovery_checks": 4,
        "oldest_source_checks": 3,
        "opnsense_denied_writes": 2,
    }
    for name, minimum in minimums.items():
        if type(metrics[name]) is not int or metrics[name] < minimum:
            fail(f"House intelligence {name} is below {minimum}")
    latency = metrics["max_narration_latency_seconds"]
    if type(latency) not in (int, float) or isinstance(latency, bool):
        fail("House intelligence narration latency is not numeric")
    if latency <= 0 or latency > 180:
        fail("House intelligence narration latency exceeds 180 seconds")
    for name in ("infrastructure_actions", "external_deliveries"):
        if type(metrics[name]) is not int or metrics[name] != 0:
            fail(f"House intelligence {name} must remain zero")

    final_state = evidence["final_state"]
    final_keys = {
        "narrator_state",
        "player_state",
        "voice_state",
        "voice_health",
        "queue_drained",
        "stale_guards",
        "normalized_states",
    }
    if not isinstance(final_state, dict) or set(final_state) != final_keys:
        fail("House intelligence final state differs from schema")
    if {key: final_state[key] for key in final_keys - {"stale_guards", "normalized_states"}} != {
        "narrator_state": "off",
        "player_state": "idle",
        "voice_state": "waiting",
        "voice_health": "healthy",
        "queue_drained": True,
    }:
        fail("House intelligence final audio state is not idle and healthy")
    if final_state["stale_guards"] != {domain: "off" for domain in DOMAINS}:
        fail("House intelligence sources were not all restored fresh")
    states = final_state["normalized_states"]
    if not isinstance(states, dict) or set(states) != set(DOMAINS):
        fail("House intelligence normalized final states are incomplete")
    allowed = {
        "frigate": {"normal", "degraded"},
        "opnsense": {"normal", "degraded"},
        "proxmox": {"normal", "degraded"},
        "victron": {"normal", "low", "critical"},
    }
    for domain, state in states.items():
        if state not in allowed[domain]:
            fail(f"House intelligence final {domain} state is not usable")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("House intelligence scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-opnsense-controller-sha256")
    parser.add_argument("--expected-opnsense-acl-sha256")
    parser.add_argument("--expected-proxmox-policy-sha256")
    parser.add_argument("--expected-frigate-policy-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_opnsense_controller_sha256,
        args.expected_opnsense_acl_sha256,
        args.expected_proxmox_policy_sha256,
        args.expected_frigate_policy_sha256,
    )
    print(
        "House-intelligence evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
