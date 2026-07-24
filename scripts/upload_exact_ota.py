#!/usr/bin/env python3
"""Upload one exact OTA artifact with ESPHome's pinned OTA implementation."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import hmac
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
from collections.abc import Iterator


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


@contextmanager
def verified_snapshot(artifact: Path, expected_sha256: str) -> Iterator[Path]:
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise RuntimeError("Expected OTA SHA-256 is invalid")
    if not artifact.is_file() or artifact.is_symlink() or artifact.stat().st_size == 0:
        raise RuntimeError("OTA artifact is missing, empty or a symlink")
    with tempfile.TemporaryDirectory(prefix="muse-exact-ota-") as directory:
        snapshot = Path(directory) / "firmware.ota.bin"
        with artifact.open("rb") as source, snapshot.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        if not hmac.compare_digest(digest(snapshot), expected_sha256):
            raise RuntimeError("OTA snapshot differs from the reviewed SHA-256")
        yield snapshot


def main() -> None:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=3232)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--secrets", type=Path, required=True)
    args = parser.parse_args()

    secrets = yaml.safe_load(args.secrets.read_text(encoding="utf-8"))
    password = secrets.get("ota_password") if isinstance(secrets, dict) else None
    if not isinstance(password, str) or len(password) < 16:
        raise SystemExit("ota_password is missing or shorter than 16 characters")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from esphome.espota2 import run_ota

    with verified_snapshot(args.artifact, args.expected_sha256) as snapshot:
        status, _ = run_ota(args.host, args.port, password, snapshot)
    if status != 0:
        raise SystemExit(status)


if __name__ == "__main__":
    main()
