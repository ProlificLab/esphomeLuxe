#!/usr/bin/env python3
"""Positive and negative fixtures for physical interpreter evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from check_interpreter_evidence import MODEL_DIGEST, PIPELINES, SCENARIOS, validate_evidence


VERSION = "2025.3.1-hal.9.0-alpha.5"
FIRMWARE_DIGEST = "a" * 64
PACKAGE_DIGEST = "b" * 64
CONFIG_DIGEST = "c" * 64
SENTENCES_DIGEST = "d" * 64


def valid_evidence(
    version: str = VERSION,
    firmware_digest: str = FIRMWARE_DIGEST,
    package_digest: str = PACKAGE_DIGEST,
    config_digest: str = CONFIG_DIGEST,
    sentences_digest: str = SENTENCES_DIGEST,
) -> dict:
    return {
        "schema_version": 1,
        "passed": True,
        "candidate": {
            "device_name": "muse-luxe-canary-bureau",
            "project_version": version,
            "firmware_sha256": firmware_digest,
            "interpreter_package_sha256": package_digest,
            "configure_script_sha256": config_digest,
            "sentences_sha256": sentences_digest,
        },
        "observer": "Household release reviewer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "model": "granite4:3b",
            "model_digest": MODEL_DIGEST,
            "pipelines": sorted(PIPELINES),
            "local_only": True,
            "tools_enabled": False,
        },
        "metrics": {
            "fr_to_en_phrases": 5,
            "en_to_fr_phrases": 5,
            "fr_to_en_max_latency_ms": 4500,
            "en_to_fr_max_latency_ms": 5000,
            "context_reset_counter_delta": 5,
            "home_actions_triggered": 0,
        },
        "scenarios": {
            name: {
                "passed": True,
                "evidence": f"Observed {name.replace('_', ' ')} on the canary.",
            }
            for name in SCENARIOS
        },
    }


class InterpreterEvidenceTests(unittest.TestCase):
    def check(self, evidence: dict) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "interpreter.json"
            path.write_text(json.dumps(evidence), encoding="utf-8")
            validate_evidence(
                path,
                VERSION,
                FIRMWARE_DIGEST,
                PACKAGE_DIGEST,
                CONFIG_DIGEST,
                SENTENCES_DIGEST,
            )

    def test_valid_evidence_passes(self) -> None:
        self.check(valid_evidence())

    def test_candidate_binding_mismatch_fails(self) -> None:
        mutations = (
            ("project_version", "other-version"),
            ("firmware_sha256", "e" * 64),
            ("interpreter_package_sha256", "f" * 64),
            ("configure_script_sha256", "0" * 64),
            ("sentences_sha256", "1" * 64),
        )
        for field, value in mutations:
            evidence = valid_evidence()
            evidence["candidate"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_runtime_must_be_pinned_local_and_tool_free(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["runtime"]["model_digest"] = "2" * 64
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["pipelines"].pop()
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["local_only"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["runtime"]["tools_enabled"] = True
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_missing_false_or_placeholder_scenario_fails(self) -> None:
        fixtures = []
        evidence = valid_evidence()
        evidence["scenarios"].pop("privacy_exit")
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["ten_minute_timeout_exit"]["passed"] = False
        fixtures.append(evidence)
        evidence = valid_evidence()
        evidence["scenarios"]["triple_click_exit"]["evidence"] = "REPLACE"
        fixtures.append(evidence)
        for index, evidence in enumerate(fixtures):
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                self.check(evidence)

    def test_metrics_are_bounded_and_reject_booleans(self) -> None:
        mutations = (
            ("fr_to_en_phrases", 4),
            ("en_to_fr_phrases", True),
            ("fr_to_en_max_latency_ms", 15001),
            ("en_to_fr_max_latency_ms", False),
            ("context_reset_counter_delta", 4),
            ("home_actions_triggered", 1),
            ("home_actions_triggered", False),
        )
        for field, value in mutations:
            evidence = valid_evidence()
            evidence["metrics"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
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
