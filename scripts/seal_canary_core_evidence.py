#!/usr/bin/env python3
"""Atomically seal reviewed core-canary metrics and their exact raw logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from check_canary_core_evidence import validate_evidence
from check_canary_deploy_readiness import file_digest, validate_readiness
from check_rollback_artifact import validate_rollback


LOG_FILES = {
    "canary_ota": "canary-ota.log",
    "reboot_recovery": "reboot-recovery.log",
    "wifi_recovery": "wifi-recovery.log",
    "ha_restart_recovery": "ha-restart-recovery.log",
    "privacy_reboot": "privacy-reboot.log",
    "tts_cycles": "tts-cycles.log",
    "rollback_artifact": "rollback-artifact.log",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def git_identity(root: Path) -> str:
    status = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain",
            "--untracked-files=normal",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        fail("Canary evidence sealing requires a clean Git worktree")
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        fail("Current Git commit is not a full lowercase SHA")
    return commit


def log_bindings(logs_dir: Path, output_dir: Path) -> dict[str, str]:
    output_root = output_dir.resolve()
    bindings: dict[str, str] = {}
    for name, filename in LOG_FILES.items():
        path = (logs_dir / filename).resolve()
        try:
            relative = path.relative_to(output_root)
        except ValueError:
            fail(f"Canary raw log must remain inside evidence directory: {filename}")
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"Canary raw log is missing or empty: {filename}")
        bindings[name] = f"sha256:{file_digest(path, 'sha256')} {relative}"
    return bindings


def seal_record(
    draft_path: Path,
    output_path: Path,
    logs_dir: Path,
    *,
    version: str,
    firmware_sha256: str,
    source_commit: str,
    device: str,
    hardware: str,
    observer: str,
    started_at: str,
    finished_at: str,
    rollback_sha256: str,
    rollback_md5: str,
    rollback_size: int,
) -> dict:
    if output_path.exists():
        fail(f"Refusing to overwrite sealed canary evidence: {output_path}")
    if not output_path.parent.is_dir():
        fail(f"Canary evidence directory does not exist: {output_path.parent}")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    if not isinstance(draft, dict):
        fail("Canary evidence draft must be a JSON object")

    draft["passed"] = True
    draft["candidate"] = {
        "device_name": device,
        "hardware": hardware,
        "project_version": version,
        "firmware_sha256": firmware_sha256,
        "source_commit": source_commit,
    }
    draft["observer"] = observer
    draft["started_at"] = started_at
    draft["finished_at"] = finished_at
    draft["logs"] = log_bindings(logs_dir, output_path.parent)
    tests = draft.get("tests")
    if not isinstance(tests, dict) or not isinstance(
        tests.get("rollback_artifact"), dict
    ):
        fail("Canary draft is missing rollback_artifact test metrics")
    tests["rollback_artifact"] = {
        "version": "2025.3.1-hal.6",
        "sha256": rollback_sha256,
        "md5": rollback_md5,
        "size_bytes": rollback_size,
        "stored_offline": tests["rollback_artifact"].get("stored_offline"),
        "verified": True,
    }

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(draft, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        temporary_path = Path(temporary_name)
        validate_evidence(
            temporary_path,
            version,
            firmware_sha256,
            source_commit,
            device,
            rollback_md5,
        )
        try:
            os.link(temporary_path, output_path)
        except FileExistsError:
            fail(f"Refusing to overwrite concurrently sealed evidence: {output_path}")
        temporary_path.unlink()
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    return draft


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("endurance_summary", type=Path)
    parser.add_argument("reviewed_sha256")
    parser.add_argument("rollback_artifact", type=Path)
    parser.add_argument("rollback_sha256")
    parser.add_argument("--logs-dir", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--observer", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--finished-at", required=True)
    parser.add_argument("--hardware", default="Raspiaudio Muse Luxe ESP32")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    source_commit = git_identity(root)
    readiness = validate_readiness(
        args.artifact,
        args.manifest,
        args.endurance_summary,
        args.reviewed_sha256,
    )
    rollback_manifest = root / "manifest_update.json"
    rollback_version = validate_rollback(
        args.rollback_artifact,
        rollback_manifest,
        args.rollback_sha256,
    )
    if rollback_version != "2025.3.1-hal.6":
        fail("Rollback validator returned an unexpected version")
    rollback_md5 = file_digest(args.rollback_artifact, "md5")
    record = seal_record(
        args.draft,
        args.output,
        args.logs_dir,
        version=readiness["version"],
        firmware_sha256=readiness["sha256"],
        source_commit=source_commit,
        device=args.device,
        hardware=args.hardware,
        observer=args.observer,
        started_at=args.started_at,
        finished_at=args.finished_at,
        rollback_sha256=args.rollback_sha256,
        rollback_md5=rollback_md5,
        rollback_size=args.rollback_artifact.stat().st_size,
    )
    print(
        "Sealed core canary evidence: "
        f"path={args.output} version={record['candidate']['project_version']} "
        f"sha256={hashlib.sha256(args.output.read_bytes()).hexdigest()}"
    )


if __name__ == "__main__":
    main()
