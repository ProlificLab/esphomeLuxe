#!/usr/bin/env python3
"""Atomically seal the completed alpha.5 endurance incident."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from check_corrective_incident import derive


def seal(output: Path, raw: Path, old_artifact: Path, old_sha256: str) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite corrective evidence: {output}")
    record = derive(raw, old_artifact, old_sha256)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("raw_jsonl", type=Path)
    parser.add_argument("old_artifact", type=Path)
    parser.add_argument("--old-sha256", required=True)
    args = parser.parse_args()
    record = seal(args.output, args.raw_jsonl, args.old_artifact, args.old_sha256)
    print(f"Sealed corrective incident: {args.output} raw_sha256={record['raw_sha256']}.")


if __name__ == "__main__":
    main()
