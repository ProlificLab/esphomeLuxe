#!/usr/bin/env python3
"""Prepare, but never apply, a consent-bound Frigate audio configuration."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import stat

try:
    import yaml
except ModuleNotFoundError:  # Only the Frigate-side file operation needs PyYAML.
    yaml = None


ALLOWED_LABELS = {"bark", "crying", "fire_alarm", "glass"}
PLACEHOLDERS = {"", "REPLACE", "UNKNOWN"}


def load_mapping(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read a Frigate configuration")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a YAML mapping in {path}")
    return value


def approved_camera(policy: dict, camera: str) -> dict:
    if policy.get("version") != 1:
        raise RuntimeError("Unsupported acoustic policy version")
    if policy.get("enabled") is not True:
        raise RuntimeError("The acoustic policy must be explicitly enabled")
    retention = policy.get("retention_days")
    if not isinstance(retention, int) or isinstance(retention, bool) or not 0 <= retention <= 1:
        raise RuntimeError("Acoustic detection retention must be between zero and one day")

    entry = (policy.get("cameras") or {}).get(camera)
    if not isinstance(entry, dict):
        raise RuntimeError(f"Camera {camera!r} is absent from the consent policy")
    if entry.get("approved") is not True:
        raise RuntimeError(f"Camera {camera!r} has no explicit room consent")
    for field in ("approved_by", "approved_at", "room"):
        if str(entry.get(field, "")).strip() in PLACEHOLDERS:
            raise RuntimeError(f"Camera {camera!r} has incomplete consent field {field}")
    try:
        approved_at = datetime.fromisoformat(str(entry["approved_at"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("approved_at must be an ISO-8601 timestamp") from error
    if approved_at.tzinfo is None:
        raise RuntimeError("approved_at must include a timezone")

    labels = entry.get("labels")
    if not isinstance(labels, dict) or not labels:
        raise RuntimeError("At least one acoustic label and threshold is required")
    unexpected = set(labels) - ALLOWED_LABELS
    if unexpected:
        raise RuntimeError(f"Unsupported acoustic labels: {sorted(unexpected)}")
    for label, threshold in labels.items():
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise RuntimeError(f"Threshold for {label} must be numeric")
        if not 0.8 <= float(threshold) <= 0.99:
            raise RuntimeError(f"Threshold for {label} must be between 0.80 and 0.99")

    min_volume = entry.get("min_volume")
    if not isinstance(min_volume, int) or isinstance(min_volume, bool) or not 200 <= min_volume <= 2000:
        raise RuntimeError("min_volume must be between 200 and 2000 RMS")
    max_not_heard = entry.get("max_not_heard")
    if not isinstance(max_not_heard, int) or isinstance(max_not_heard, bool) or not 5 <= max_not_heard <= 30:
        raise RuntimeError("max_not_heard must be between 5 and 30 seconds")
    if entry.get("input_role") not in {"detect", "record"}:
        raise RuntimeError("input_role must explicitly select detect or record")
    return entry


def prepare(config: dict, policy: dict, camera: str) -> dict:
    entry = approved_camera(policy, camera)
    if (config.get("audio") or {}).get("enabled") is True:
        raise RuntimeError("Global Frigate audio must remain disabled")
    if (config.get("audio_transcription") or {}).get("enabled") is True:
        raise RuntimeError("Global audio transcription must remain disabled")
    cameras = config.get("cameras") or {}
    if camera not in cameras:
        raise RuntimeError(f"Camera {camera!r} does not exist in Frigate")
    streams = (config.get("go2rtc") or {}).get("streams") or {}
    if camera not in streams:
        raise RuntimeError(f"Camera {camera!r} has no same-name go2rtc restream")

    camera_config = cameras[camera]
    inputs = (camera_config.get("ffmpeg") or {}).get("inputs") or []
    selected = [item for item in inputs if entry["input_role"] in (item.get("roles") or [])]
    if len(selected) != 1:
        raise RuntimeError("The selected input role must identify exactly one stream")
    path = str(selected[0].get("path", ""))
    if not path.startswith(("rtsp://127.0.0.1:8554/", "rtsp://localhost:8554/")):
        raise RuntimeError("Audio detection must use the local go2rtc restream")
    if any("audio" in (item.get("roles") or []) for item in inputs):
        raise RuntimeError(f"Camera {camera!r} already has an audio input")
    selected[0].setdefault("roles", []).append("audio")

    labels = entry["labels"]
    camera_config["audio"] = {
        "enabled": True,
        "max_not_heard": entry["max_not_heard"],
        "min_volume": entry["min_volume"],
        "listen": sorted(labels),
        "filters": {
            label: {"threshold": float(threshold)}
            for label, threshold in sorted(labels.items())
        },
    }
    camera_config["audio_transcription"] = {"enabled": False}

    global_alerts = (((config.get("review") or {}).get("alerts") or {}).get("labels"))
    camera_alerts = (((camera_config.get("review") or {}).get("alerts") or {}).get("labels"))
    effective_alerts = camera_alerts if camera_alerts is not None else global_alerts
    if effective_alerts is None:
        effective_alerts = ["person", "car"]
    camera_config.setdefault("review", {}).setdefault("alerts", {})["labels"] = [
        label for label in effective_alerts if label not in labels
    ]

    retention = policy["retention_days"]
    camera_config.setdefault("record", {}).setdefault("detections", {}).setdefault(
        "retain", {}
    ).update({"days": retention, "mode": "motion"})
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--camera", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.resolve() == args.config.resolve():
        raise RuntimeError("Refusing to modify the active Frigate config in place")
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {args.output}")

    candidate = prepare(load_mapping(args.config), load_mapping(args.policy), args.camera)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        # Frigate's own Python environment includes the parser for its YAML config.
        yaml.safe_dump(candidate, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    args.output.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"Prepared unapplied candidate {args.output} (mode 0600).")
    print("Validate it with Frigate before any backup, replacement or restart.")


if __name__ == "__main__":
    main()
