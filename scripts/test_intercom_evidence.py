#!/usr/bin/env python3
"""Positive and negative fixtures for two-satellite intercom evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_intercom_evidence import (
    DEVICE_ROOMS,
    ROOM_PLAYERS,
    SCENARIOS,
    validate_evidence,
)


VERSION = "2025.3.1-hal.9.0-alpha.5"
DIGESTS = [character * 64 for character in "abcdef012"]


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = DIGESTS[0],
    package_digest: str = DIGESTS[1],
    base_digest: str = DIGESTS[2],
    sentences_digest: str = DIGESTS[3],
    ui_digest: str = DIGESTS[4],
    recovery_digest: str = DIGESTS[5],
    checker_digest: str = DIGESTS[6],
    model_digest: str = DIGESTS[7],
    ha_test_digest: str = DIGESTS[8],
) -> dict:
    calls_a = 20
    calls_b = 20
    accepted = 8
    relays_a = 10
    relays_b = 10
    audible = 100
    attempts = relays_a + relays_b + 1
    errors = 1
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "intercom_package_sha256": package_digest,
            "base_package_sha256": base_digest,
            "sentences_sha256": sentences_digest,
            "ui_package_sha256": ui_digest,
            "recovery_package_sha256": recovery_digest,
            "safety_checker_sha256": checker_digest,
            "model_test_sha256": model_digest,
            "ha_test_sha256": ha_test_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "observed_players": list(ROOM_PLAYERS.values()),
        "observed_devices": list(DEVICE_ROOMS),
        "runtime": {
            "room_players": dict(ROOM_PLAYERS),
            "device_rooms": dict(DEVICE_ROOMS),
            "ring_timeout_seconds": 45,
            "session_timeout_seconds": 300,
            "maximum_transcript_characters": 240,
            "relay_queue_capacity": 5,
            "transport": "transcribed_push_to_talk",
            "origin_policy": "explicit_room_or_trusted_device_event",
            "single_click": "accept_or_manual_listen",
            "double_click": "decline_or_hangup",
            "raw_audio": False,
            "duplex": False,
        },
        "metrics": {
            "calls_bureau_to_cuisine": calls_a,
            "calls_cuisine_to_bureau": calls_b,
            "accepted_calls": accepted,
            "declined_calls": 4,
            "participant_hangups": 4,
            "ring_timeouts": 2,
            "session_timeouts": 2,
            "relays_bureau_to_cuisine": relays_a,
            "relays_cuisine_to_bureau": relays_b,
            "button_actions": 4,
            "session_mismatch_rejections": 4,
            "unavailable_player_rejections": 3,
            "audible_actions": audible,
            "carillons_heard": audible,
            "visible_led_signals": audible,
            "relay_attempts": attempts,
            "recognition_errors": errors,
            "recognition_error_rate": errors / attempts,
            "p95_transcript_to_speech_latency_seconds": 8.2,
            "max_transcript_to_speech_latency_seconds": 12.5,
            "ghost_channels": 0,
            "raw_audio_sessions": 0,
            "transcript_artifacts": 0,
            "external_deliveries": 0,
            "music_restore_errors": 0,
            "urgent_preemption_errors": 0,
        },
        "final_state": {
            "enabled": "off",
            "status": "idle",
            "caller_room": "",
            "target_room": "",
            "session_id": "",
            "last_event": "",
            "ring_timer": "idle",
            "session_timer": "idle",
            "player_states": {
                "media_player.raspiaudio_muse_luxe": "idle",
                "media_player.muse_luxe_cuisine": "idle",
            },
            "voice_states": {"muse-luxe": "waiting", "muse-luxe-cuisine": "waiting"},
            "voice_health": {"muse-luxe": "healthy", "muse-luxe-cuisine": "healthy"},
            "music_restored": True,
            "active_channel": False,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on both satellites.",
            }
            for name in SCENARIOS
        },
    }


class IntercomEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "intercom.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(path, VERSION, *DIGESTS)

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        fields = (
            "project_version",
            "firmware_sha256",
            "intercom_package_sha256",
            "base_package_sha256",
            "sentences_sha256",
            "ui_package_sha256",
            "recovery_package_sha256",
            "safety_checker_sha256",
            "model_test_sha256",
            "ha_test_sha256",
        )
        for field in fields:
            evidence = valid_evidence()
            evidence["candidate"][field] = "9" * 64 if field != "project_version" else "other"
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_targets_runtime_and_scenarios_are_closed(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["observed_players"].reverse()
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["observed_devices"][1] = "unknown-device"
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["duplex"] = True
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"].pop("old_queued_relay_is_rejected_after_new_session")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["transcript_is_absent_from_helpers"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_reject_shortcuts_and_booleans(self) -> None:
        for field, value in (
            ("calls_bureau_to_cuisine", 19),
            ("calls_cuisine_to_bureau", True),
            ("accepted_calls", 7),
            ("relays_bureau_to_cuisine", 9),
            ("button_actions", 3),
            ("session_mismatch_rejections", 3),
            ("carillons_heard", 79),
            ("visible_led_signals", 79),
            ("recognition_error_rate", 0.11),
            ("p95_transcript_to_speech_latency_seconds", 15.1),
            ("max_transcript_to_speech_latency_seconds", 30.1),
            ("ghost_channels", False),
            ("transcript_artifacts", 1),
            ("music_restore_errors", 1),
        ):
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_final_state_is_exact(self) -> None:
        for field, value in (
            ("enabled", "on"),
            ("status", "connected"),
            ("session_id", "leftover"),
            ("active_channel", True),
            ("music_restored", False),
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
