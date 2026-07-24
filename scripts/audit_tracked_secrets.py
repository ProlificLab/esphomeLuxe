#!/usr/bin/env python3
"""Audit Git-tracked files for private values without printing those values."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


SENSITIVE_KEY_MARKERS = ("password", "secret", "token", "encryption_key")
PLACEHOLDER_MARKERS = ("replace", "example", "placeholder", "changeme")
PROHIBITED_NAMES = {"secrets.yaml", ".env", "id_rsa", "id_ed25519"}
SUSPICIOUS_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def tracked_files(root: Path) -> list[Path]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    return [root / os.fsdecode(item) for item in output.split(b"\0") if item]


def private_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"Private secrets file does not exist: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip().strip("'\"")
        lowered = value.lower()
        if not any(marker in key.lower() for marker in SENSITIVE_KEY_MARKERS):
            continue
        decoded_placeholder = False
        try:
            decoded = base64.b64decode(value, validate=True)
            decoded_placeholder = bool(decoded) and set(decoded) <= {0, ord("0")}
        except (binascii.Error, ValueError):
            pass
        if (
            len(value) < 8
            or any(marker in lowered for marker in PLACEHOLDER_MARKERS)
            or set(value) <= {"0", "=", "A"}
            or decoded_placeholder
        ):
            continue
        values[key] = value
    return values


def audit(root: Path, private_secrets: Path) -> dict[str, object]:
    files = tracked_files(root)
    secrets = private_values(private_secrets)
    exact_matches: list[dict[str, str]] = []
    suspicious_matches: list[dict[str, str]] = []
    prohibited: list[str] = []

    for path in files:
        relative = str(path.relative_to(root))
        if path.name in PROHIBITED_NAMES or path.suffix in {".pem", ".p12", ".key"}:
            prohibited.append(relative)
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for key, value in secrets.items():
            if value in content:
                exact_matches.append({"key": key, "path": relative})
        for label, pattern in SUSPICIOUS_PATTERNS.items():
            if pattern.search(content):
                suspicious_matches.append({"pattern": label, "path": relative})

    findings = {
        "exact_secret_matches": sorted(exact_matches, key=lambda item: (item["path"], item["key"])),
        "suspicious_pattern_matches": sorted(
            suspicious_matches, key=lambda item: (item["path"], item["pattern"])
        ),
        "prohibited_tracked_files": sorted(prohibited),
    }
    passed = not any(findings.values())
    return {
        "schema_version": 1,
        "passed": passed,
        "tracked_file_count": len(files),
        "private_secret_keys_checked": len(secrets),
        "findings": findings,
    }


def write_atomic(path: Path, report: dict[str, object]) -> None:
    if not path.parent.is_dir():
        fail(f"Audit output directory does not exist: {path.parent}")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(report, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--private-secrets", type=Path, default=Path("secrets.yaml"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-private-keys", type=int, default=0)
    args = parser.parse_args()
    report = audit(args.root.resolve(), args.private_secrets.resolve())
    if report["private_secret_keys_checked"] < args.require_private_keys:
        fail(
            "Too few non-placeholder private secret values were checked: "
            f"{report['private_secret_keys_checked']} < {args.require_private_keys}"
        )
    if args.output is not None:
        write_atomic(args.output, report)
    print(json.dumps(report, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
