#!/usr/bin/env python3
"""Activate verified local Muse secrets and retire the OTA transition file."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

import yaml

from check_secret_rotation_bundle import validate_bundle


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_mapping(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("Secret activation input is not a YAML mapping")
    return value


def atomic_copy(source: Path, destination: Path) -> None:
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.",
            suffix=".tmp", delete=False,
        ) as output:
            temporary = output.name
            os.fchmod(output.fileno(), 0o600)
            output.write(source.read_bytes())
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def atomic_manifest(path: Path, manifest: dict[str, object]) -> None:
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as output:
            temporary = output.name
            os.fchmod(output.fileno(), 0o600)
            json.dump(manifest, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def activate(bundle: Path, active: Path) -> dict[str, object]:
    manifest_path = bundle / "rotation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status") if isinstance(manifest, dict) else None
    new_path = bundle / "secrets.yaml"
    transition_path = bundle / "transition-ota.yaml"
    if status == "prepared_offline":
        validate_bundle(bundle)
    elif status != "activated_verified":
        fail("Rotation bundle is not prepared or resumable")
    if not active.is_file() or active.is_symlink() or active.stat().st_uid != os.getuid():
        fail("Active secrets must be a current-user regular file")
    if active.stat().st_mode & 0o077:
        fail("Active secrets permissions must be private")
    new = read_mapping(new_path)
    current = read_mapping(active)
    transition = read_mapping(transition_path) if transition_path.exists() else {}
    old_ota = transition.get("ota_password")
    if current.get("ota_password") not in {old_ota, new.get("ota_password")}:
        fail("Active secrets do not match the reviewed old or new OTA credential")
    if current.get("ota_password") == new.get("ota_password") and current != new:
        fail("Active secrets only partially match the reviewed new credential set")
    if current != new:
        atomic_copy(new_path, active)
    manifest["status"] = "activated_verified"
    manifest["transition_retired"] = True
    atomic_manifest(manifest_path, manifest)
    transition_path.unlink(missing_ok=True)
    return {"status": "activated_verified", "transition_retired": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("active_secrets", type=Path)
    args = parser.parse_args()
    print(json.dumps(activate(args.bundle.absolute(), args.active_secrets.absolute()), sort_keys=True))


if __name__ == "__main__":
    main()
