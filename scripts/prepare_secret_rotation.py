#!/usr/bin/env python3
"""Prepare private Muse credential rotation files without contacting a device."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil

import yaml


ROTATED_KEYS = ("api_encryption_key", "ota_password", "fallback_ap_password")


def fail(message: str) -> None:
    raise RuntimeError(message)


def require_private_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        fail("Current secrets must be a regular file")
    metadata = path.stat()
    if metadata.st_uid != os.getuid():
        fail("Current secrets must be owned by the current user")
    if metadata.st_mode & 0o077:
        fail("Current secrets permissions must be 0600 or stricter")


def load_current(path: Path) -> dict[str, object]:
    require_private_file(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("Current secrets must be a YAML mapping")
    for key in ROTATED_KEYS:
        secret = value.get(key)
        if not isinstance(secret, str) or len(secret) < 8:
            fail(f"Current secrets are missing a usable {key}")
    return value


def generate_values() -> dict[str, str]:
    return {
        "api_encryption_key": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        "ota_password": secrets.token_urlsafe(32),
        "fallback_ap_password": secrets.token_urlsafe(18),
    }


def validate_generated(current: dict[str, object], generated: dict[str, str]) -> None:
    if set(generated) != set(ROTATED_KEYS) or len(set(generated.values())) != len(ROTATED_KEYS):
        fail("Generated credentials are incomplete or not independent")
    if any(generated[key] == current[key] for key in ROTATED_KEYS):
        fail("Generated credentials must differ from current credentials")
    try:
        api_key = base64.b64decode(generated["api_encryption_key"], validate=True)
    except ValueError as error:
        fail(f"Generated API encryption key is invalid: {error}")
    if len(api_key) != 32:
        fail("Generated API encryption key must decode to 32 bytes")
    if len(generated["ota_password"]) < 32:
        fail("Generated OTA password is too short")
    fallback_length = len(generated["fallback_ap_password"])
    if fallback_length < 16 or fallback_length > 63:
        fail("Generated fallback AP password is outside WPA limits")


def write_private_yaml(path: Path, value: dict[str, object]) -> None:
    payload = yaml.safe_dump(value, sort_keys=False, default_flow_style=False).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def write_private_json(path: Path, value: dict[str, object]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def prepare(current_path: Path, output_directory: Path) -> dict[str, object]:
    current = load_current(current_path)
    generated = generate_values()
    validate_generated(current, generated)
    if output_directory.exists() or output_directory.is_symlink():
        fail("Rotation output directory already exists")
    if not output_directory.parent.is_dir() or output_directory.parent.is_symlink():
        fail("Rotation output parent must be a regular directory")

    output_directory.mkdir(mode=0o700)
    output_directory.chmod(0o700)
    try:
        rotated = dict(current)
        rotated.update(generated)
        write_private_yaml(output_directory / "secrets.yaml", rotated)
        write_private_yaml(
            output_directory / "transition-ota.yaml",
            {"ota_password": current["ota_password"]},
        )
        manifest: dict[str, object] = {
            "schema_version": 1,
            "status": "prepared_offline",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rotated_keys": list(ROTATED_KEYS),
            "transition_keys": ["ota_password"],
            "files": {
                "new_secrets": "secrets.yaml",
                "transition_ota": "transition-ota.yaml",
            },
            "required_permissions": {"directory": "0700", "files": "0600"},
            "network_actions_performed": 0,
        }
        write_private_json(output_directory / "rotation-manifest.json", manifest)
        directory_fd = os.open(output_directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return manifest
    except Exception:
        shutil.rmtree(output_directory, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current_secrets", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    manifest = prepare(args.current_secrets.absolute(), args.output_directory.absolute())
    print(
        "Prepared offline credential rotation: "
        f"directory={args.output_directory} status={manifest['status']}."
    )


if __name__ == "__main__":
    main()
