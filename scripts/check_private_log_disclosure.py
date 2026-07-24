#!/usr/bin/env python3
"""Fail if private secret values occur in specified qualification logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_tracked_secrets import private_values


def check(secrets_path: Path, paths: list[Path], required: int = 3) -> dict[str, object]:
    values = private_values(secrets_path)
    if len(values) < required:
        raise RuntimeError("Too few real private values for log-disclosure check")
    checked: list[str] = []
    resolved_paths: set[Path] = set()
    disclosed: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise RuntimeError(f"Qualification log is missing, empty or a symlink: {path}")
        resolved = path.resolve()
        if resolved in resolved_paths:
            raise RuntimeError("Qualification disclosure logs must be distinct files")
        resolved_paths.add(resolved)
        content = path.read_text(encoding="utf-8", errors="replace")
        checked.append(path.name)
        for key, value in values.items():
            if value in content:
                disclosed.append({"key": key, "path": path.name})
    return {
        "schema_version": 1,
        "passed": not disclosed,
        "private_secret_keys_checked": len(values),
        "log_count": len(paths),
        "logs": checked,
        "disclosures": disclosed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-secrets", type=Path, required=True)
    parser.add_argument("--require-private-keys", type=int, default=3)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    report = check(args.private_secrets, args.paths, args.require_private_keys)
    print(json.dumps(report, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
