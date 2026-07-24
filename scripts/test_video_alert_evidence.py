#!/usr/bin/env python3
"""Positive and negative fixtures for physical video-alert evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_video_alert_evidence import CAMERAS, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
DIGESTS = [character * 64 for character in "abcdef0"]


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = DIGESTS[0],
    package_digest: str = DIGESTS[1],
    base_digest: str = DIGESTS[2],
    checker_digest: str = DIGESTS[3],
    model_digest: str = DIGESTS[4],
    mqtt_digest: str = DIGESTS[5],
    frigate_digest: str = DIGESTS[6],
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "alert_package_sha256": package_digest,
            "base_package_sha256": base_digest,
            "safety_checker_sha256": checker_digest,
            "model_test_sha256": model_digest,
            "mqtt_provision_sha256": mqtt_digest,
            "frigate_policy_sha256": frigate_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "allowed_cameras": list(CAMERAS),
            "minimum_confidence": 0.75,
            "cooldown_seconds": 60,
            "history_capacity": 7,
            "maximum_event_age_seconds": 30,
            "future_tolerance_seconds": 5,
            "target": "media_player.raspiaudio_muse_luxe",
            "priority": "normal",
            "chime": True,
            "automation_mode": "single",
        },
        "metrics": {
            "accepted_announcements": 5,
            "audible_announcements": 5,
            "dedup_rejections": 2,
            "cooldown_rejections": 1,
            "stale_rejections": 2,
            "content_filter_rejections": 8,
            "night_rejections": 1,
            "maximum_history_size": 7,
            "max_delivery_latency_seconds": 18.5,
            "delivery_errors": 0,
            "critical_actions": 0,
            "external_deliveries": 0,
        },
        "final_state": {
            "alerts_enabled": "off",
            "night_mode": "off",
            "mqtt_available": "on",
            "player_state": "idle",
            "voice_state": "waiting",
            "voice_health": "healthy",
            "history_size": 7,
            "last_event_in_history": True,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} through MQTT.",
            }
            for name in SCENARIOS
        },
    }


class VideoAlertEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "video-alert.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, VERSION, *DIGESTS)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "alert_package_sha256",
            "base_package_sha256",
            "safety_checker_sha256",
            "model_test_sha256",
            "mqtt_provision_sha256",
            "frigate_policy_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = "1" * 64 if field != "project_version" else "other"
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_and_scenarios_are_closed(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["history_capacity"] = 1
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["allowed_cameras"].append("cuisine")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"].pop("same_event_update_after_other_event_is_not_repeated")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["night_mode_is_silent"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["unreviewed_camera_is_silent"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_reject_shortcuts_and_booleans(self) -> None:
        for field, value in (
            ("accepted_announcements", 4),
            ("audible_announcements", 4),
            ("dedup_rejections", 1),
            ("cooldown_rejections", 0),
            ("stale_rejections", 1),
            ("content_filter_rejections", 7),
            ("night_rejections", True),
            ("maximum_history_size", 6),
            ("max_delivery_latency_seconds", 61),
            ("delivery_errors", False),
            ("critical_actions", 1),
            ("external_deliveries", 1),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_final_state_is_exact(self) -> None:
        for field, value in (
            ("alerts_enabled", "on"),
            ("mqtt_available", "off"),
            ("player_state", "playing"),
            ("history_size", 8),
            ("last_event_in_history", False),
        ):
            evidence = valid_evidence()
            evidence["final_state"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
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
