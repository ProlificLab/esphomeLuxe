#!/usr/bin/env python3
"""Validate read-only Proxmox entities and optionally narrate them on the Muse."""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
PLAYER = "media_player.raspiaudio_muse_luxe"


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
    with urllib.request.urlopen(req, timeout=300) as response:
        if response.status == 204:
            return None
        return json.load(response)


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


def wait_player(token: str, timeout: int = 300) -> str:
    deadline = time.monotonic() + timeout
    played = False
    while time.monotonic() < deadline:
        current = request(f"/api/states/{PLAYER}", token)["state"]
        if current in {"playing", "buffering"}:
            played = True
        if played and current == "idle":
            return current
        time.sleep(0.5)
    raise RuntimeError(f"Muse narration did not complete; played={played}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--announce", action="store_true")
    args = parser.parse_args()
    token = access_token()

    with open(
        "/config/.storage/core.config_entries", encoding="utf-8"
    ) as entries_file:
        entries = json.load(entries_file)["data"]["entries"]
    entry = next((item for item in entries if item["domain"] == "proxmoxve"), None)
    if not entry:
        raise RuntimeError("The Proxmox VE config entry is missing")

    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        registry = json.load(registry_file)["data"]["entities"]
    proxmox_entities = [
        item for item in registry if item.get("platform") == "proxmoxve"
    ]
    buttons = [
        item for item in proxmox_entities if item["entity_id"].startswith("button.")
    ]
    enabled_buttons = [
        item["entity_id"] for item in buttons if item.get("disabled_by") != "user"
    ]
    if enabled_buttons:
        raise RuntimeError(f"Proxmox control buttons remain enabled: {enabled_buttons}")
    exposed = [
        item["entity_id"]
        for item in proxmox_entities
        if item.get("options", {})
        .get("conversation", {})
        .get("should_expose", False)
    ]
    if exposed:
        raise RuntimeError(f"Proxmox entities are exposed to Assist: {exposed}")

    states = {item["entity_id"]: item for item in request("/api/states", token)}
    expected = {
        "binary_sensor.chuwi_pve_status": "on",
        "sensor.chuwi_pve_status": "online",
        "sensor.haos_status": "running",
        "sensor.frigate_status": "running",
        "sensor.muse_proxmox_status": "normal",
        "binary_sensor.muse_proxmox_data_stale": "off",
    }
    for entity_id, expected_state in expected.items():
        current = states.get(entity_id, {}).get("state")
        if current != expected_state:
            raise RuntimeError(
                f"Unexpected Proxmox state {entity_id}={current}; "
                f"expected {expected_state}"
            )
    normalized = states["sensor.muse_proxmox_status"]
    if normalized["attributes"].get("credential_role") != "PVEAuditor":
        raise RuntimeError("Normalized Proxmox state does not declare PVEAuditor")
    if normalized["attributes"].get("controls_exposed") is not False:
        raise RuntimeError("Normalized Proxmox state claims controls are exposed")

    final_player_state = "not_requested"
    if args.announce:
        request(
            "/api/services/script/turn_on",
            token,
            {
                "entity_id": "script.muse_narrate_house_status",
                "variables": {"target": PLAYER},
            },
        )
        final_player_state = wait_player(token)

    print(
        "PASS Home Assistant Proxmox "
        f"entry={entry['entry_id']} entities={len(proxmox_entities)} "
        f"buttons_disabled={len(buttons)} assist_exposed=0 "
        f"node=online haos=running frigate=running stale=off "
        f"announcement={final_player_state}"
    )


if __name__ == "__main__":
    main()
