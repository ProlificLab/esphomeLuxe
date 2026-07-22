#!/usr/bin/env python3
"""Validate a private credential-rotation bundle without exposing its values."""

from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

import yaml

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
}
PLACEHOLDERS = ("replace", "example", "placeholder", "changeme")


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


def validate_bundle(directory: Path) -> dict[str, object]:
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
        or manifest["schema_version"] != 1
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
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = validate_bundle(args.directory.absolute())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
