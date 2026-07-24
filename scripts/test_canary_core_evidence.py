#!/usr/bin/env python3
"""Positive and negative fixtures for core canary physical evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_canary_core_evidence import validate_evidence


VERSION = "2026.1.0-hal.10-beta.1"
FIRMWARE_SHA = "a" * 64
SOURCE_COMMIT = "b" * 40
DEVICE = "muse-luxe-canary-bureau"
ROLLBACK_MD5 = "cedf966640caccbabba098bcf22f7645"


def healthy() -> dict[str, object]:
    return {"final_state": "waiting", "final_health": "healthy", "final_error": ""}


def recovery(duration: float) -> dict[str, object]:
    return {
        "attempted": 10,
        "completed": 10,
        "max_recovery_seconds": duration,
        "manual_interventions": 0,
        **healthy(),
    }


def valid_evidence() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": DEVICE,
            "hardware": "Raspiaudio Muse Luxe ESP32",
            "project_version": VERSION,
            "firmware_sha256": FIRMWARE_SHA,
            "source_commit": SOURCE_COMMIT,
        },
        "observer": "Household release reviewer",
        "started_at": (now - timedelta(hours=2)).isoformat(),
        "finished_at": now.isoformat(),
        "limits": {
            "max_wifi_recovery_seconds": 10,
            "max_ha_recovery_seconds": 10,
            "max_reboot_recovery_seconds": 20,
        },
        "logs": {name: "sha256:PLACEHOLDER log" for name in (
            "canary_ota",
            "reboot_recovery",
            "wifi_recovery",
            "ha_restart_recovery",
            "privacy_reboot",
            "tts_cycles",
            "rollback_artifact",
        )},
        "tests": {
            "canary_ota": {
                "attempted": 1,
                "completed": 1,
                "installed_sha256_match": True,
                "exact_version": True,
                "manual_interventions": 0,
                **healthy(),
            },
            "reboot_recovery": recovery(18.5),
            "wifi_recovery": recovery(8.2),
            "ha_restart_recovery": recovery(7.4),
            "privacy_reboot": {"persisted": True, "cleared": True, **healthy()},
            "tts_cycles": {
                "requested": 100,
                "completed": 100,
                "heard": 100,
                "failures": 0,
                "ring_buffer_resets": 0,
                "voice_errors": 0,
                **healthy(),
            },
            "rollback_artifact": {
                "version": "2025.3.1-hal.6",
                "sha256": "c" * 64,
                "md5": ROLLBACK_MD5,
                "size_bytes": 1900000,
                "stored_offline": True,
                "verified": True,
            },
        },
    }


def write_log_fixtures(directory: Path, evidence: dict[str, object]) -> None:
    for index, name in enumerate(sorted(evidence["logs"])):
        path = directory / f"{name}.log"
        path.write_text(f"reviewed {name} fixture {index}\n", encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence["logs"][name] = f"sha256:{digest} {path.name}"


class CanaryCoreEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "canary-core.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, evidence: dict[str, object]) -> None:
        write_log_fixtures(self.path.parent, evidence)
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        validate_evidence(
            self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, DEVICE, ROLLBACK_MD5
        )

    def test_exact_complete_record_passes(self) -> None:
        self.validate(valid_evidence())

    def test_candidate_identity_drift_fails(self) -> None:
        for field, value in (
            ("project_version", "other"),
            ("firmware_sha256", "0" * 64),
            ("source_commit", "0" * 40),
            ("device_name", "other-device"),
        ):
            evidence = valid_evidence()
            evidence["candidate"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_each_recovery_count_limit_and_cleanup_are_closed(self) -> None:
        for name in ("reboot_recovery", "wifi_recovery", "ha_restart_recovery"):
            for field, value in (
                ("completed", 9),
                ("manual_interventions", 1),
                ("max_recovery_seconds", 21),
                ("final_health", "degraded"),
            ):
                evidence = valid_evidence()
                evidence["tests"][name][field] = value
                with self.subTest(name=name, field=field), self.assertRaises(RuntimeError):
                    self.validate(evidence)

    def test_recovery_deadline_boundary_is_strict(self) -> None:
        for name, duration in (
            ("wifi_recovery", 10),
            ("ha_restart_recovery", 10),
            ("reboot_recovery", 20),
        ):
            evidence = valid_evidence()
            evidence["tests"][name]["max_recovery_seconds"] = duration
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_ota_privacy_and_tts_failures_are_rejected(self) -> None:
        mutations = (
            ("canary_ota", "installed_sha256_match", False),
            ("canary_ota", "manual_interventions", 1),
            ("privacy_reboot", "cleared", False),
            ("tts_cycles", "heard", 99),
            ("tts_cycles", "ring_buffer_resets", 1),
            ("tts_cycles", "voice_errors", 1),
        )
        for name, field, value in mutations:
            evidence = valid_evidence()
            evidence["tests"][name][field] = value
            with self.subTest(name=name, field=field), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_rollback_identity_and_retention_are_closed(self) -> None:
        for field, value in (
            ("md5", "0" * 32),
            ("sha256", "bad"),
            ("size_bytes", 0),
            ("stored_offline", False),
            ("verified", False),
        ):
            evidence = valid_evidence()
            evidence["tests"]["rollback_artifact"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_schema_time_and_passed_are_closed(self) -> None:
        mutations = []
        value = valid_evidence(); value["passed"] = False; mutations.append(value)
        value = valid_evidence(); value["extra"] = True; mutations.append(value)
        value = valid_evidence(); value["finished_at"] = "2020-01-01T00:00:00+00:00"; mutations.append(value)
        for index, evidence in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.validate(evidence)

    def test_missing_tampered_or_escaping_logs_are_rejected(self) -> None:
        evidence = valid_evidence()
        write_log_fixtures(self.path.parent, evidence)
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        (self.path.parent / "tts_cycles.log").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(
                self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, DEVICE, ROLLBACK_MD5
            )
        evidence = valid_evidence()
        write_log_fixtures(self.path.parent, evidence)
        evidence["logs"]["canary_ota"] = evidence["logs"]["tts_cycles"]
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(
                self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, DEVICE, ROLLBACK_MD5
            )
        evidence = valid_evidence()
        write_log_fixtures(self.path.parent, evidence)
        evidence["logs"]["canary_ota"] = "sha256:" + "0" * 64 + " ../escape.log"
        self.path.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            validate_evidence(
                self.path, VERSION, FIRMWARE_SHA, SOURCE_COMMIT, DEVICE, ROLLBACK_MD5
            )


if __name__ == "__main__":
    unittest.main()
