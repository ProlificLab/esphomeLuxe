#!/usr/bin/env python3
"""Positive and negative fixtures for the acoustic guardian tooling."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile

from prepare_frigate_acoustic_guardian import prepare


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_acoustic_guardian_safety.py"


def fixture() -> tuple[dict, dict]:
    config = {
        "go2rtc": {"streams": {"sonnette": "rtsp://camera.invalid/stream"}},
        "review": {"alerts": {"labels": ["person", "car", "fire_alarm"]}},
        "record": {"detections": {"retain": {"days": 14}}},
        "cameras": {
            "sonnette": {
                "ffmpeg": {
                    "inputs": [
                        {
                            "path": "rtsp://127.0.0.1:8554/sonnette_sub",
                            "roles": ["detect"],
                        },
                        {
                            "path": "rtsp://127.0.0.1:8554/sonnette",
                            "roles": ["record"],
                        },
                    ]
                },
                "record": {"enabled": True},
            }
        },
    }
    policy = {
        "version": 1,
        "enabled": True,
        "retention_days": 1,
        "cameras": {
            "sonnette": {
                "approved": True,
                "approved_by": "household-owner",
                "approved_at": "2026-07-22T04:00:00+02:00",
                "room": "entree_exterieure",
                "input_role": "detect",
                "min_volume": 500,
                "max_not_heard": 10,
                "labels": {"fire_alarm": 0.9},
            }
        },
    }
    return config, policy


def rejected(config: dict, policy: dict, message: str) -> None:
    try:
        prepare(config, policy, "sonnette")
    except RuntimeError:
        return
    raise RuntimeError(f"Unsafe acoustic fixture was accepted: {message}")


def main() -> None:
    subprocess.run(["python3", str(CHECKER)], check=True)
    config, policy = fixture()
    candidate = prepare(deepcopy(config), deepcopy(policy), "sonnette")
    camera = candidate["cameras"]["sonnette"]
    assert "audio" in camera["ffmpeg"]["inputs"][0]["roles"]
    assert camera["audio"]["enabled"] is True
    assert camera["audio_transcription"]["enabled"] is False
    assert camera["record"]["detections"]["retain"]["days"] == 1
    assert "fire_alarm" not in camera["review"]["alerts"]["labels"]

    unsafe = deepcopy(policy)
    unsafe["cameras"]["sonnette"]["approved"] = False
    rejected(deepcopy(config), unsafe, "missing consent")
    unsafe = deepcopy(policy)
    unsafe["retention_days"] = 3
    rejected(deepcopy(config), unsafe, "long retention")
    unsafe = deepcopy(policy)
    unsafe["cameras"]["sonnette"]["labels"] = {"speech": 0.9}
    rejected(deepcopy(config), unsafe, "continuous speech class")
    unsafe_config = deepcopy(config)
    unsafe_config["cameras"]["sonnette"]["ffmpeg"]["inputs"][0]["path"] = (
        "rtsp://192.168.1.99/stream"
    )
    rejected(unsafe_config, deepcopy(policy), "direct camera connection")
    unsafe = deepcopy(policy)
    unsafe["cameras"]["sonnette"]["approved_at"] = "2026-07-22"
    rejected(deepcopy(config), unsafe, "timezone-free consent")
    unsafe_config = deepcopy(config)
    unsafe_config["audio"] = {"enabled": True}
    rejected(unsafe_config, deepcopy(policy), "global audio")
    unsafe_config = deepcopy(config)
    unsafe_config["audio_transcription"] = {"enabled": True}
    rejected(unsafe_config, deepcopy(policy), "global transcription")

    package = (ROOT / "home-assistant/packages/muse_acoustic_guardian.yaml").read_text()
    with tempfile.TemporaryDirectory() as temporary:
        package_path = Path(temporary) / "unsafe.yaml"
        package_path.write_text(package + "\nautomation:\n  - actions:\n      - action: siren.turn_on\n")
        result = subprocess.run(
            ["python3", str(CHECKER), "--package", str(package_path)],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError("Critical acoustic action was accepted")
    print("Acoustic guardian positive and negative fixtures passed.")


if __name__ == "__main__":
    main()
