#!/usr/bin/env python3
"""Positive and negative fixtures for physical video-review evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_video_review_evidence import CAMERA_MAP, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
PACKAGE_DIGEST = "b" * 64
DASHBOARD_DIGEST = "c" * 64
PROVISIONER_DIGEST = "d" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    package_digest: str = PACKAGE_DIGEST,
    dashboard_digest: str = DASHBOARD_DIGEST,
    provisioner_digest: str = PROVISIONER_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "ha_package_sha256": package_digest,
            "dashboard_sha256": dashboard_digest,
            "provisioner_sha256": provisioner_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "camera_map": dict(CAMERA_MAP),
            "destination": "ha_dashboard",
            "authenticated_frontend": True,
            "window_seconds": 300,
            "maximum_image_age_seconds": 30,
            "maximum_image_before_event_seconds": 5,
        },
        "metrics": {
            "accepted_events": {camera: 1 for camera in CAMERA_MAP},
            "below_threshold_rejections": 1,
            "unmapped_camera_rejections": 1,
            "non_person_rejections": 1,
            "stale_image_rejections": 1,
            "expired_windows": 2,
            "ha_restart_cycles": 1,
            "public_urls_or_tokens": 0,
            "external_deliveries": 0,
        },
        "final_state": {
            "enabled": False,
            "destination": "disabled",
            "camera": "none",
            "window_active": False,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} in Home Assistant.",
            }
            for name in SCENARIOS
        },
    }


class VideoReviewEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "video-review.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                PACKAGE_DIGEST,
                DASHBOARD_DIGEST,
                PROVISIONER_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "ha_package_sha256",
            "dashboard_sha256",
            "provisioner_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = "other" if field == "project_version" else "e" * 64
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_and_final_state_are_exact(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["camera_map"].pop("sonnette")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["window_seconds"] = 301
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["authenticated_frontend"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["final_state"]["destination"] = "ha_dashboard"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("no_public_url_or_token")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["window_expiry_hides_card"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["unmapped_camera_rejected"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_are_complete_and_reject_booleans(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["metrics"]["accepted_events"]["sonnette"] = 0
        fixtures.append(evidence)
        for field, value in (
            ("below_threshold_rejections", 0),
            ("expired_windows", 1),
            ("ha_restart_cycles", True),
            ("public_urls_or_tokens", 1),
            ("external_deliveries", False),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
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
