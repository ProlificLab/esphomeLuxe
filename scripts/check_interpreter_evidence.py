#!/usr/bin/env python3
"""Validate candidate-bound physical bilingual-interpreter evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


MODEL_DIGEST = "89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f"
PIPELINES = {
    "Interprete - Anglais vers francais",
    "Interprete - Francais vers anglais",
}
SCENARIOS = {
    "command_phrase_translated_not_executed",
    "context_reset_each_exit",
    "continuous_listening_led_visible",
    "direction_swap",
    "english_piper_audible",
    "en_to_fr_five_phrases",
    "fr_to_en_five_phrases",
    "french_piper_audible",
    "ha_restart_exit",
    "no_transcript_reachable_after_exit",
    "previous_pipeline_restored_each_exit",
    "privacy_exit",
    "subsequent_house_query_has_no_translation_context",
    "ten_minute_timeout_exit",
    "triple_click_exit",
}
PLACEHOLDERS = ("pending", "todo", "tbd", "replace", "unknown", "not tested")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_text(value: object, label: str, minimum: int = 8) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        fail(f"Interpreter {label} is missing or too short")
    text = value.strip()
    if any(marker in text.lower() for marker in PLACEHOLDERS):
        fail(f"Interpreter {label} is still a placeholder")
    return text


def require_digest(value: object, label: str) -> str:
    digest = require_text(value, label, minimum=64)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"Interpreter {label} is not a lowercase SHA-256")
    return digest


def parse_observed_at(value: object) -> datetime:
    text = require_text(value, "observed_at")
    try:
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Interpreter observed_at is invalid: {error}")
    if observed.tzinfo is None:
        fail("Interpreter observed_at must include a timezone")
    now = datetime.now(timezone.utc)
    observed_utc = observed.astimezone(timezone.utc)
    if observed_utc > now + timedelta(minutes=5):
        fail("Interpreter observed_at is in the future")
    if observed_utc < now - timedelta(days=30):
        fail("Interpreter evidence is older than 30 days")
    return observed_utc


def validate_result(result: object, label: str) -> None:
    if not isinstance(result, dict) or set(result) != {"passed", "evidence"}:
        fail(f"Interpreter {label} keys differ from schema")
    if result["passed"] is not True:
        fail(f"Interpreter {label} did not pass")
    require_text(result["evidence"], f"{label} evidence")


def validate_evidence(
    path: Path,
    expected_version: str | None = None,
    expected_firmware_sha256: str | None = None,
    expected_package_sha256: str | None = None,
    expected_config_sha256: str | None = None,
    expected_sentences_sha256: str | None = None,
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
        "scenarios",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        fail("Interpreter evidence keys differ from schema")
    if evidence["schema_version"] != 1 or evidence["passed"] is not True:
        fail("Interpreter evidence did not pass with schema version 1")

    candidate = evidence["candidate"]
    candidate_keys = {
        "device_name",
        "project_version",
        "firmware_sha256",
        "interpreter_package_sha256",
        "configure_script_sha256",
        "sentences_sha256",
    }
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        fail("Interpreter candidate identity is incomplete")
    require_text(candidate["device_name"], "candidate device_name", minimum=3)
    version = require_text(candidate["project_version"], "candidate version")
    firmware_digest = require_digest(
        candidate["firmware_sha256"], "firmware_sha256"
    )
    package_digest = require_digest(
        candidate["interpreter_package_sha256"], "interpreter_package_sha256"
    )
    config_digest = require_digest(
        candidate["configure_script_sha256"], "configure_script_sha256"
    )
    sentences_digest = require_digest(
        candidate["sentences_sha256"], "sentences_sha256"
    )
    expected = (
        (version, expected_version, "firmware version"),
        (firmware_digest, expected_firmware_sha256, "firmware SHA-256"),
        (package_digest, expected_package_sha256, "package SHA-256"),
        (config_digest, expected_config_sha256, "config script SHA-256"),
        (sentences_digest, expected_sentences_sha256, "sentences SHA-256"),
    )
    for actual, wanted, label in expected:
        if wanted is not None and actual != wanted:
            fail(f"Interpreter {label} does not match")
    require_text(evidence["observer"], "observer")
    parse_observed_at(evidence["observed_at"])

    runtime = evidence["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {
        "model",
        "model_digest",
        "pipelines",
        "local_only",
        "tools_enabled",
    }:
        fail("Interpreter runtime identity differs from schema")
    if runtime["model"] != "granite4:3b" or runtime["model_digest"] != MODEL_DIGEST:
        fail("Interpreter runtime model or digest differs from policy")
    if not isinstance(runtime["pipelines"], list) or set(runtime["pipelines"]) != PIPELINES:
        fail("Interpreter runtime pipelines differ from the closed pair")
    if len(runtime["pipelines"]) != len(PIPELINES):
        fail("Interpreter runtime pipelines contain duplicates")
    if runtime["local_only"] is not True or runtime["tools_enabled"] is not False:
        fail("Interpreter runtime is not local and tool-free")

    metrics = evidence["metrics"]
    metric_keys = {
        "fr_to_en_phrases",
        "en_to_fr_phrases",
        "fr_to_en_max_latency_ms",
        "en_to_fr_max_latency_ms",
        "context_reset_counter_delta",
        "home_actions_triggered",
    }
    if not isinstance(metrics, dict) or set(metrics) != metric_keys:
        fail("Interpreter metrics differ from schema")
    for direction in ("fr_to_en", "en_to_fr"):
        phrases = metrics[f"{direction}_phrases"]
        latency = metrics[f"{direction}_max_latency_ms"]
        if type(phrases) is not int or phrases < 5:
            fail(f"Interpreter {direction} requires at least five phrases")
        if type(latency) is not int or not 1 <= latency <= 15000:
            fail(f"Interpreter {direction} latency exceeds 15 seconds")
    if (
        type(metrics["context_reset_counter_delta"]) is not int
        or metrics["context_reset_counter_delta"] < 5
    ):
        fail("Interpreter did not prove context reset for all five exit paths")
    if (
        type(metrics["home_actions_triggered"]) is not int
        or metrics["home_actions_triggered"] != 0
    ):
        fail("Interpreter triggered a Home Assistant action")

    scenarios = evidence["scenarios"]
    if not isinstance(scenarios, dict) or set(scenarios) != SCENARIOS:
        fail("Interpreter scenarios differ from the closed checklist")
    for name, result in scenarios.items():
        validate_result(result, f"scenario {name}")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-firmware-sha256")
    parser.add_argument("--expected-package-sha256")
    parser.add_argument("--expected-config-sha256")
    parser.add_argument("--expected-sentences-sha256")
    args = parser.parse_args()
    evidence = validate_evidence(
        args.evidence,
        args.expected_version,
        args.expected_firmware_sha256,
        args.expected_package_sha256,
        args.expected_config_sha256,
        args.expected_sentences_sha256,
    )
    print(
        "Interpreter evidence passed: "
        f"version={evidence['candidate']['project_version']} "
        f"scenarios={len(evidence['scenarios'])}."
    )


if __name__ == "__main__":
    main()
