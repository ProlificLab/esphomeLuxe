#!/usr/bin/env python3
"""Configure the Proxmox VE integration from an ephemeral token secret file."""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8123"
DOMAIN = "proxmoxve"


def request(path: str, token: str, data: dict | None = None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def access_token() -> str:
    with open("/config/.storage/auth", encoding="utf-8") as auth_file:
        auth = json.load(auth_file)
    refresh_token = next(
        item
        for item in auth["data"]["refresh_tokens"]
        if item["token_type"] == "normal"
    )
    token_body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token["token"],
            "client_id": refresh_token["client_id"],
        }
    ).encode()
    with urllib.request.urlopen(
        urllib.request.Request(BASE_URL + "/auth/token", data=token_body),
        timeout=30,
    ) as response:
        return json.load(response)["access_token"]


def existing_entry() -> dict | None:
    with open(
        "/config/.storage/core.config_entries", encoding="utf-8"
    ) as entries_file:
        entries = json.load(entries_file)["data"]["entries"]
    return next((item for item in entries if item["domain"] == DOMAIN), None)


def expect_form(result: dict, step_id: str) -> None:
    if result.get("type") != "form" or result.get("step_id") != step_id:
        raise RuntimeError(f"Unexpected Proxmox config flow step: {result}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", default="homeassistant")
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--token-id", default="homeassistant")
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument(
        "--verify-ssl",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Verify the Proxmox TLS certificate; disabled for a local self-signed cert",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if entry := existing_entry():
            print(
                json.dumps(
                    {
                        "status": "already_configured",
                        "entry_id": entry["entry_id"],
                        "title": entry["title"],
                    }
                )
            )
            return
        secret = args.secret_file.read_text(encoding="utf-8").strip()
        if not secret:
            raise RuntimeError("The ephemeral Proxmox token secret is empty")
        token = access_token()
        flow = request(
            "/api/config/config_entries/flow",
            token,
            {"handler": DOMAIN, "show_advanced_options": True},
        )
        expect_form(flow, "user")
        flow = request(
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            token,
            {
                "auth_method": "pve",
                "host": args.host,
                "username": args.username,
                "port": args.port,
                "token": True,
                "verify_ssl": args.verify_ssl,
            },
        )
        expect_form(flow, "user_auth")
        result = request(
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            token,
            {"token_id": args.token_id, "token_value": secret},
        )
        if result.get("type") != "create_entry":
            raise RuntimeError(f"Proxmox integration setup failed: {result}")
        entry = existing_entry() or result.get("result", {})
        if entry.get("domain") not in (None, DOMAIN):
            raise RuntimeError(f"Unexpected config entry created: {entry}")
        print(
            json.dumps(
                {
                    "status": "configured",
                    "entry_id": entry.get("entry_id"),
                    "title": entry.get("title", result.get("title")),
                }
            )
        )
    finally:
        try:
            os.unlink(args.secret_file)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
