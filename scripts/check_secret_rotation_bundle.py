#!/usr/bin/env python3
"""Validate a private credential-rotation bundle without exposing its values."""

from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timedelta, timezone
import json
import hashlib
import os
from pathlib import Path
import re

import yaml

from check_endurance_summary import validate_summary
from prepare_secret_rotation import ROTATED_KEYS


MANIFEST_KEYS = {
    "schema_version",
    "status",
    "generated_at",
    "rotated_keys",
    "transition_keys",
    "files",
    "required_permissions",
    "network_actions_performed",
    "endurance",
}
PLACEHOLDERS = ("replace", "example", "placeholder", "changeme")
VERSION_PATTERN = r"[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+"


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_private(path: Path, mode: int, kind: str) -> None:
    if path.is_symlink() or (not path.is_dir() if kind == "directory" else not path.is_file()):
        fail(f"Rotation {kind} is missing, not regular or a symlink")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != mode:
        fail(f"Rotation {kind} owner or permissions are invalid")


def parse_time(value: object) -> str:
    if not isinstance(value, str):
        fail("Rotation generated_at is not text")
    try:
        generated = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"Rotation generated_at is invalid: {error}")
    if generated.tzinfo is None:
        fail("Rotation generated_at must include a timezone")
    generated = generated.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if generated > now + timedelta(minutes=5) or generated < now - timedelta(days=30):
        fail("Rotation bundle is outside the 30-day preparation window")
    return generated.isoformat()


def load_mapping(path: Path, label: str) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        fail(f"Rotation {label} must be a YAML mapping with text keys")
    return value


def digest(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        fail("Rotation endurance summary must be a non-empty regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_bundle(
    directory: Path,
    endurance_summary: Path | None = None,
    expected_version: str | None = None,
) -> dict[str, object]:
    require_private(directory, 0o700, "directory")
    manifest_path = directory / "rotation-manifest.json"
    new_path = directory / "secrets.yaml"
    transition_path = directory / "transition-ota.yaml"
    for path in (manifest_path, new_path, transition_path):
        require_private(path, 0o600, "file")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        fail(f"Rotation manifest is invalid: {error}")
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        fail("Rotation manifest keys differ from schema")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 2
        or manifest["status"] != "prepared_offline"
        or manifest["rotated_keys"] != list(ROTATED_KEYS)
        or manifest["transition_keys"] != ["ota_password"]
        or manifest["files"]
        != {"new_secrets": "secrets.yaml", "transition_ota": "transition-ota.yaml"}
        or manifest["required_permissions"] != {"directory": "0700", "files": "0600"}
        or type(manifest["network_actions_performed"]) is not int
        or manifest["network_actions_performed"] != 0
    ):
        fail("Rotation manifest identity or safety contract is invalid")
    generated_at = parse_time(manifest["generated_at"])
    endurance = manifest["endurance"]
    if not isinstance(endurance, dict) or set(endurance) != {
        "passed", "project_version", "finished_at", "summary_sha256"
    }:
        fail("Rotation endurance binding keys differ from schema")
    if (
        endurance["passed"] is not True
        or not isinstance(endurance["project_version"], str)
        or re.fullmatch(VERSION_PATTERN, endurance["project_version"]) is None
        or not isinstance(endurance["summary_sha256"], str)
        or len(endurance["summary_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in endurance["summary_sha256"])
    ):
        fail("Rotation endurance identity is invalid")
    endurance_finished_at = parse_time(endurance["finished_at"])
    if datetime.fromisoformat(endurance_finished_at) > datetime.fromisoformat(generated_at):
        fail("Rotation bundle was generated before its endurance finished")
    if expected_version is not None and endurance["project_version"] != expected_version:
        fail("Rotation endurance version differs from the expected candidate")
    if endurance_summary is not None:
        summary = validate_summary(endurance_summary, endurance["project_version"])
        if (
            digest(endurance_summary) != endurance["summary_sha256"]
            or summary["finished_at"] != endurance["finished_at"]
        ):
            fail("Rotation endurance summary differs from the bound evidence")

    rotated = load_mapping(new_path, "new secrets")
    transition = load_mapping(transition_path, "transition secrets")
    if set(transition) != {"ota_password"}:
        fail("Rotation transition must contain only ota_password")
    values: list[str] = []
    for key in ROTATED_KEYS:
        value = rotated.get(key)
        if not isinstance(value, str) or any(marker in value.lower() for marker in PLACEHOLDERS):
            fail(f"Rotation new {key} is missing or recognizable as a fixture")
        values.append(value)
    if len(set(values)) != len(values):
        fail("Rotation new credentials are not independent")
    try:
        decoded_api = base64.b64decode(rotated["api_encryption_key"], validate=True)
    except (binascii.Error, ValueError) as error:
        fail(f"Rotation API encryption key is invalid: {error}")
    if len(decoded_api) != 32 or set(decoded_api) <= {0, ord("0")}:
        fail("Rotation API encryption key is not a real 32-byte value")
    if len(rotated["ota_password"]) < 32:
        fail("Rotation new OTA password is too short")
    if not 16 <= len(rotated["fallback_ap_password"]) <= 63:
        fail("Rotation fallback AP password is outside WPA limits")
    old_ota = transition.get("ota_password")
    if not isinstance(old_ota, str) or len(old_ota) < 16 or old_ota == rotated["ota_password"]:
        fail("Rotation transition OTA credential is invalid or not retired")

    return {
        "schema_version": 1,
        "passed": True,
        "status": manifest["status"],
        "generated_at": generated_at,
        "rotated_key_count": len(ROTATED_KEYS),
        "transition_key_count": len(transition),
        "network_actions_performed": 0,
        "endurance_summary_bound": True,
        "project_version": endurance["project_version"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--endurance-summary", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    result = validate_bundle(
        args.directory.absolute(), args.endurance_summary, args.expected_version
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
