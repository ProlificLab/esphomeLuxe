#!/usr/bin/env python3
"""Install a pinned Frigate Home Assistant integration archive safely."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile


DESTINATION = Path("/config/custom_components/frigate")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    if DESTINATION.exists():
        manifest = json.loads((DESTINATION / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("version") == args.version:
            print(json.dumps({"status": "already_installed", "version": args.version}))
            return

    with tempfile.TemporaryDirectory(prefix="frigate-hass-") as temporary:
        root = Path(temporary)
        with tarfile.open(args.archive, "r:gz") as archive:
            members = []
            for member in archive.getmembers():
                parts = PurePosixPath(member.name).parts
                try:
                    marker = parts.index("custom_components")
                except ValueError:
                    continue
                if parts[marker : marker + 2] != ("custom_components", "frigate"):
                    continue
                relative = Path(*parts[marker + 2 :])
                if not relative.parts or ".." in relative.parts or member.issym() or member.islnk():
                    continue
                member.name = str(relative)
                members.append(member)
            if not members:
                raise RuntimeError("Pinned archive contains no Frigate component")
            archive.extractall(root, members=members, filter="data")

        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("version") != args.version:
            raise RuntimeError(f"Unexpected Frigate integration manifest: {manifest}")

        backup = None
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        if DESTINATION.exists():
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup = DESTINATION.with_name(f"frigate.pre-{args.version}-{stamp}")
            shutil.move(DESTINATION, backup)
        shutil.copytree(root, DESTINATION)
        (DESTINATION / ".muse-source.json").write_text(
            json.dumps({"version": args.version, "commit": args.commit}) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "status": "installed",
                "version": args.version,
                "commit": args.commit,
                "backup": backup.name if backup else None,
            }
        )
    )


if __name__ == "__main__":
    main()
