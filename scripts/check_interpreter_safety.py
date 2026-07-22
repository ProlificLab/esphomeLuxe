#!/usr/bin/env python3
"""Enforce the static safety contract of the local interpreter package."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ALLOWED_ACTIONS = {
    "input_boolean.turn_off",
    "input_boolean.turn_on",
    "input_select.select_option",
    "input_text.set_value",
    "logbook.log",
    "esphome.muse_luxe_clear_conversation_context",
    "script.muse_announce",
    "script.muse_start_interpreter",
    "script.muse_stop_interpreter",
    "select.select_option",
    "switch.turn_off",
    "switch.turn_on",
    "timer.cancel",
    "timer.start",
}
ALLOWED_SWITCHES = {
    "switch.raspiaudio_muse_luxe_continuous_conversation",
    "switch.raspiaudio_muse_luxe_privacy_mode",
}
ALLOWED_SELECTS = {
    "select.raspiaudio_muse_luxe_assistant",
    "select.raspiaudio_muse_luxe_assistant_2",
}


def require(source: str, marker: str, label: str) -> None:
    if marker not in source:
        raise RuntimeError(f"Missing interpreter {label}: {marker}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        type=Path,
        default=root / "home-assistant/packages/muse_interpreter.yaml",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=root / "scripts/configure_interpreter.py",
    )
    args = parser.parse_args()
    package = args.package.read_text(encoding="utf-8")
    config = args.config.read_text(encoding="utf-8")
    recovery = (root / "packages/recovery.yaml").read_text(encoding="utf-8")
    diagnostics = (root / "packages/diagnostics.yaml").read_text(encoding="utf-8")
    firmware = (root / "luxe_microWW.yaml").read_text(encoding="utf-8")

    required_package_markers = (
        'duration: "00:10:00"',
        "maximum_session_seconds: 600",
        "tools_enabled: \"{{ false }}\"",
        "history_previous_rounds: 1",
        "context_cleared_on_exit: \"{{ true }}\"",
        "switch.raspiaudio_muse_luxe_privacy_mode",
        "switch.raspiaudio_muse_luxe_continuous_conversation",
        "input_text.muse_interpreter_previous_pipeline",
        "muse_interpreter_exit_on_timeout",
        "muse_interpreter_recover_after_ha_restart",
    )
    for marker in required_package_markers:
        require(package, marker, "package guard")

    actions = set(
        re.findall(r"^\s*-\s+action:\s+([a-z0-9_.]+)\s*$", package, re.MULTILINE)
    )
    if forbidden := actions - ALLOWED_ACTIONS:
        raise RuntimeError(f"Interpreter actions are not allowlisted: {sorted(forbidden)}")
    if re.search(r"^\s*-\s+action:\s*[\"']?\{\{", package, re.MULTILINE):
        raise RuntimeError("Templated interpreter actions are forbidden")

    switches = set(
        re.findall(r"(?:entity_id:\s*|-\s+)(switch\.[a-z0-9_]+)", package)
    )
    if forbidden := switches - ALLOWED_SWITCHES:
        raise RuntimeError(f"Interpreter switch targets are not allowlisted: {sorted(forbidden)}")
    selects = set(
        re.findall(r"(?:entity_id:\s*|-\s+)(select\.[a-z0-9_]+)", package)
    )
    if forbidden := selects - ALLOWED_SELECTS:
        raise RuntimeError(f"Interpreter select targets are not allowlisted: {sorted(forbidden)}")

    required_config_markers = (
        'MODEL = "granite4:3b"',
        'MODEL_DIGEST = "89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f"',
        '"max_history": 1',
        '"num_ctx": 2048',
        '"think": False',
        '"tools": False',
        "never as an instruction",
        '"prefer_local_intents": False',
        '"stt_engine": "stt.faster_whisper"',
        '"tts_engine": "tts.piper"',
        '"history_previous_rounds": 1',
    )
    for marker in required_config_markers:
        require(config, marker, "agent guard")
    if re.search(r"[\"']llm_hass_api[\"']\s*:", config):
        raise RuntimeError("Interpreter agents must never receive a Home Assistant LLM API")

    require(recovery, "action: clear_conversation_context", "firmware API action")
    require(recovery, "id(va).reset_conversation_id();", "firmware context reset")
    require(diagnostics, "name: Voice Context Resets", "firmware reset telemetry")
    require(firmware, 'version: "2025.3.1-hal.9.0-alpha.3"', "firmware version")

    print("Interpreter safety contract passed: local, tool-free and time-bounded.")


if __name__ == "__main__":
    main()
