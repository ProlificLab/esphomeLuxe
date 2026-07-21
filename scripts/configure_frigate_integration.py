#!/usr/bin/env python3
"""Configure the official Frigate integration using an ephemeral password."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
DOMAIN = "frigate"


def access_token() -> str:
    with open("/config/.storage/auth", encoding="utf-8") as auth_file:
        auth = json.load(auth_file)
    refresh_token = next(
        item
        for item in auth["data"]["refresh_tokens"]
        if item["token_type"] == "normal"
    )
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token["token"],
            "client_id": refresh_token["client_id"],
        }
    ).encode()
    with urllib.request.urlopen(
        urllib.request.Request(BASE_URL + "/auth/token", data=body), timeout=30
    ) as response:
        return json.load(response)["access_token"]


def request(path: str, token: str, data: dict | None = None) -> dict:
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def existing_entry() -> dict | None:
    with open(
        "/config/.storage/core.config_entries", encoding="utf-8"
    ) as entries_file:
        entries = json.load(entries_file)["data"]["entries"]
    return next((entry for entry in entries if entry["domain"] == DOMAIN), None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://192.168.1.20:8971")
    parser.add_argument("--username", default="homeassistant_muse")
    parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        if entry := existing_entry():
            print(json.dumps({"status": "already_configured", "entry_id": entry["entry_id"]}))
            return
        password = args.password_file.read_text(encoding="utf-8").strip()
        if not password:
            raise RuntimeError("The ephemeral Frigate password is empty")
        token = access_token()
        flow = request(
            "/api/config/config_entries/flow",
            token,
            {"handler": DOMAIN, "show_advanced_options": True},
        )
        if flow.get("type") != "form" or flow.get("step_id") != "user":
            raise RuntimeError(f"Unexpected Frigate flow start: {flow}")
        result = request(
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            token,
            {
                "url": args.url,
                "validate_ssl": False,
                "username": args.username,
                "password": password,
            },
        )
        if result.get("type") != "create_entry":
            raise RuntimeError(f"Frigate integration setup failed: {result}")
        entry = existing_entry() or result.get("result", {})
        print(json.dumps({"status": "configured", "entry_id": entry.get("entry_id")}))
    finally:
        try:
            os.unlink(args.password_file)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
