#!/usr/bin/env python3
"""Positive and negative fixtures for physical offline-rescue evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_offline_rescue_evidence import CLIPS, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
PACKAGE_DIGEST = "b" * 64
COMPONENT_DIGEST = "c" * 64
CARD_DIGEST = "d" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    package_digest: str = PACKAGE_DIGEST,
    component_digest: str = COMPONENT_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "rescue_package_sha256": package_digest,
            "offline_component_sha256": component_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "card": {
            "volume_label": "MUSE_RESCUE",
            "manifest_sha256_before": CARD_DIGEST,
            "manifest_sha256_after": CARD_DIGEST,
            "files": sorted(CLIPS),
        },
        "metrics": {
            "clip_play_counts": {name: 1 for name in CLIPS},
            "ha_disconnect_cycles": 1,
            "ha_reconnect_cycles": 1,
            "reboots_while_rescue": 1,
            "unexpected_media_errors": 0,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in SCENARIOS
        },
    }


class OfflineRescueEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "offline-rescue.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                PACKAGE_DIGEST,
                COMPONENT_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        mutations = (
            ("project_version", "other-version"),
            ("firmware_sha256", "e" * 64),
            ("rescue_package_sha256", "f" * 64),
            ("offline_component_sha256", "0" * 64),
        )
        for field, value in mutations:
            evidence = valid_evidence()
            evidence["candidate"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_card_identity_or_manifest_change_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["card"]["volume_label"] = "ORDINARY"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["card"]["files"].pop()
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["card"]["manifest_sha256_after"] = "e" * 64
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("privacy_stops_and_blocks_entry")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["reboot_restores_rescue"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["stop_double_press"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_require_every_clip_and_exact_cycles(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["metrics"]["clip_play_counts"]["EVAC.WAV"] = 0
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["ha_disconnect_cycles"] = 0
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["unexpected_media_errors"] = 1
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["ha_reconnect_cycles"] = True
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["metrics"]["unexpected_media_errors"] = False
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_stale_or_future_time_fails(self) -> None:
        for delta in (timedelta(days=-31), timedelta(minutes=6)):
            evidence = valid_evidence()
            evidence["observed_at"] = (
                datetime.now(timezone.utc) + delta
            ).isoformat()
            with self.subTest(delta=delta), self.assertRaises(RuntimeError):
                self.check(evidence)


if __name__ == "__main__":
    unittest.main()
