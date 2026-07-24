#!/usr/bin/env python3
"""Create or rotate the dedicated Home Assistant Frigate viewer account."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, "/opt/frigate")

from frigate.api.auth import hash_password, validate_password_strength


USERNAME = "homeassistant_muse"
DATABASE = Path("/config/frigate.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotate", action="store_true")
    return parser.parse_args()


def backup_database(connection: sqlite3.Connection) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = DATABASE.with_name(f"frigate.db.pre-ha-viewer-{stamp}")
    with sqlite3.connect(destination) as backup:
        connection.backup(backup)
    destination.chmod(0o600)
    return destination


def main() -> None:
    args = parse_args()
    password = sys.stdin.read().strip()
    valid, message = validate_password_strength(password)
    if not valid:
        raise RuntimeError(message or "Frigate viewer password is too weak")

    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        row = connection.execute(
            "SELECT role FROM user WHERE username = ?", (USERNAME,)
        ).fetchone()
        if row is not None and not args.rotate:
            if row[0] != "viewer":
                backup = backup_database(connection)
                connection.execute(
                    "UPDATE user SET role = 'viewer' WHERE username = ?", (USERNAME,)
                )
                connection.commit()
                status = "role_repaired"
            else:
                backup = None
                status = "already_configured"
        else:
            backup = backup_database(connection)
            password_hash = hash_password(password, iterations=600000)
            if row is None:
                connection.execute(
                    "INSERT INTO user "
                    "(username, password_hash, notification_tokens, role, password_changed_at) "
                    "VALUES (?, ?, '[]', 'viewer', CURRENT_TIMESTAMP)",
                    (USERNAME, password_hash),
                )
                status = "configured"
            else:
                connection.execute(
                    "UPDATE user SET password_hash = ?, role = 'viewer', "
                    "password_changed_at = CURRENT_TIMESTAMP WHERE username = ?",
                    (password_hash, USERNAME),
                )
                status = "rotated"
            connection.commit()
        print(
            json.dumps(
                {
                    "status": status,
                    "username": USERNAME,
                    "role": "viewer",
                    "backup": backup.name if backup else None,
                }
            )
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
