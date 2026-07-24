#!/usr/bin/env python3
"""Reconfigure Home Assistant infrastructure integrations onto VLAN addresses."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
TARGETS = {
    "proxmoxve": "10.10.30.10",
    "frigate": "http://10.10.30.20:8971",
}


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


def request(path: str, token: str, data: dict) -> dict:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def entries() -> list[dict]:
    with open(
        "/config/.storage/core.config_entries", encoding="utf-8"
    ) as entries_file:
        return json.load(entries_file)["data"]["entries"]


def start_reconfigure(token: str, entry: dict) -> dict:
    return request(
        "/api/config/config_entries/flow",
        token,
        {"handler": entry["domain"], "entry_id": entry["entry_id"]},
    )


def submit(token: str, flow: dict, data: dict) -> dict:
    return request(
        f"/api/config/config_entries/flow/{flow['flow_id']}", token, data
    )


def migrate_frigate(token: str, entry: dict) -> str:
    if entry["data"].get("url") == TARGETS["frigate"]:
        return "already_current"
    flow = start_reconfigure(token, entry)
    data = {**entry["data"], "url": TARGETS["frigate"]}
    result = submit(token, flow, data)
    if result.get("type") != "abort" or result.get("reason") != "reconfigure_successful":
        raise RuntimeError(f"Frigate reconfiguration failed: {result}")
    return "migrated"


def migrate_proxmox(token: str, entry: dict) -> str:
    if entry["data"].get("host") == TARGETS["proxmoxve"]:
        return "already_current"
    flow = start_reconfigure(token, entry)
    base = {
        "auth_method": entry["data"]["auth_method"],
        "host": TARGETS["proxmoxve"],
        "username": entry["data"]["username"].split("@", 1)[0],
        "port": entry["data"]["port"],
        "token": entry["data"].get("token", False),
        "verify_ssl": entry["data"].get("verify_ssl", False),
    }
    if entry["data"]["auth_method"] == "other":
        base["realm"] = entry["data"]["realm"]
    auth_flow = submit(token, flow, base)
    if auth_flow.get("type") != "form" or auth_flow.get("step_id") != "reconfigure_auth":
        raise RuntimeError(f"Unexpected Proxmox authentication flow: {auth_flow}")
    auth = (
        {
            "token_id": entry["data"]["token_id"],
            "token_value": entry["data"]["token_value"],
        }
        if entry["data"].get("token")
        else {"password": entry["data"]["password"]}
    )
    result = submit(token, auth_flow, auth)
    if result.get("type") != "abort" or result.get("reason") != "reconfigure_successful":
        raise RuntimeError(f"Proxmox reconfiguration failed: {result}")
    return "migrated"


def main() -> None:
    token = access_token()
    by_domain = {
        entry["domain"]: entry
        for entry in entries()
        if entry["domain"] in TARGETS and entry.get("disabled_by") is None
    }
    missing = TARGETS.keys() - by_domain.keys()
    if missing:
        raise RuntimeError(f"Missing active integrations: {sorted(missing)}")
    results = {
        "proxmoxve": migrate_proxmox(token, by_domain["proxmoxve"]),
        "frigate": migrate_frigate(token, by_domain["frigate"]),
    }
    print(json.dumps({"status": "ok", "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
