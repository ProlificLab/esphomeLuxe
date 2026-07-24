#!/usr/bin/env python3
"""Positive and negative fixtures for house-intelligence evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_house_intelligence_evidence import (
    DOMAINS,
    ROLES,
    SCENARIOS,
    THRESHOLDS,
    validate_evidence,
)


VERSION = "2025.3.1-hal.9.0-alpha.5"
DIGESTS = [character * 64 for character in "abcdef0"]


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = DIGESTS[0],
    package_digest: str = DIGESTS[1],
    controller_digest: str = DIGESTS[2],
    acl_digest: str = DIGESTS[3],
    proxmox_digest: str = DIGESTS[4],
    frigate_digest: str = DIGESTS[5],
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "ha_package_sha256": package_digest,
            "opnsense_controller_sha256": controller_digest,
            "opnsense_acl_sha256": acl_digest,
            "proxmox_policy_sha256": proxmox_digest,
            "frigate_policy_sha256": frigate_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "domains": list(DOMAINS),
            "stale_thresholds": dict(THRESHOLDS),
            "credential_roles": dict(ROLES),
            "narration_target": "media_player.raspiaudio_muse_luxe",
        },
        "metrics": {
            "successful_narrations": 5,
            "fresh_domain_checks": 4,
            "stale_domain_checks": 4,
            "recovery_checks": 4,
            "oldest_source_checks": 3,
            "opnsense_denied_writes": 2,
            "max_narration_latency_seconds": 42.5,
            "infrastructure_actions": 0,
            "external_deliveries": 0,
        },
        "final_state": {
            "narrator_state": "off",
            "player_state": "idle",
            "voice_state": "waiting",
            "voice_health": "healthy",
            "queue_drained": True,
            "stale_guards": {domain: "off" for domain in DOMAINS},
            "normalized_states": {
                "frigate": "degraded",
                "opnsense": "normal",
                "proxmox": "normal",
                "victron": "normal",
            },
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in SCENARIOS
        },
    }


class HouseIntelligenceEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "house-intelligence.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, VERSION, *DIGESTS[:6])

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "ha_package_sha256",
            "opnsense_controller_sha256",
            "opnsense_acl_sha256",
            "proxmox_policy_sha256",
            "frigate_policy_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = "1" * 64 if field != "project_version" else "other"
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_is_exact(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["stale_thresholds"]["opnsense_seconds"] = 600
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["credential_roles"]["proxmox"] = "Administrator"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["domains"].append("other")
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_scenarios_are_closed(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("victron_oldest_required_source_wins")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["opnsense_post_returns_405"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["combined_fresh_narration"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_reject_shortcuts_and_booleans(self) -> None:
        for field, value in (
            ("successful_narrations", 4),
            ("fresh_domain_checks", True),
            ("stale_domain_checks", 3),
            ("recovery_checks", 3),
            ("oldest_source_checks", 2),
            ("opnsense_denied_writes", 1),
            ("max_narration_latency_seconds", 181),
            ("infrastructure_actions", False),
            ("external_deliveries", 1),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_final_state_requires_fresh_safe_cleanup(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["final_state"]["queue_drained"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["stale_guards"]["frigate"] = "on"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["normalized_states"]["proxmox"] = "unavailable"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_stale_future_or_naive_time_fails(self) -> None:
        values = (
            (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
            (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat(),
            datetime.now().replace(tzinfo=None).isoformat(),
        )
        for value in values:
            evidence = valid_evidence()
            evidence["observed_at"] = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.check(evidence)


if __name__ == "__main__":
    unittest.main()
