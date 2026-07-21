#!/usr/bin/env python3
"""Disable Proxmox control buttons and verify no entity is exposed to Assist."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
DOMAIN = "proxmoxve"


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


def registry_entities() -> list[dict]:
    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        entities = json.load(registry_file)["data"]["entities"]
    return [item for item in entities if item.get("platform") == DOMAIN]


async def disable_buttons(token: str, entity_ids: list[str]) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BASE_URL + "/api/websocket") as websocket:
            greeting = await websocket.receive_json()
            if greeting.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected WebSocket greeting: {greeting}")
            await websocket.send_json({"type": "auth", "access_token": token})
            auth_result = await websocket.receive_json()
            if auth_result.get("type") != "auth_ok":
                raise RuntimeError(f"Home Assistant authentication failed: {auth_result}")
            for message_id, entity_id in enumerate(entity_ids, start=1):
                await websocket.send_json(
                    {
                        "id": message_id,
                        "type": "config/entity_registry/update",
                        "entity_id": entity_id,
                        "disabled_by": "user",
                    }
                )
                result = await websocket.receive_json()
                if not result.get("success"):
                    raise RuntimeError(f"Could not disable {entity_id}: {result}")


def main() -> None:
    entities = registry_entities()
    if not entities:
        raise RuntimeError("No Proxmox VE entities exist to harden")
    exposed = [
        item["entity_id"]
        for item in entities
        if item.get("options", {})
        .get("conversation", {})
        .get("should_expose", False)
    ]
    if exposed:
        raise RuntimeError(f"Proxmox entities are exposed to Assist: {exposed}")
    buttons = [
        item["entity_id"]
        for item in entities
        if item["entity_id"].startswith("button.")
        and item.get("disabled_by") != "user"
    ]
    if buttons:
        asyncio.run(disable_buttons(access_token(), buttons))
    remaining = [
        item["entity_id"]
        for item in registry_entities()
        if item["entity_id"].startswith("button.")
        and item.get("disabled_by") != "user"
    ]
    if remaining:
        raise RuntimeError(f"Proxmox buttons remain enabled: {remaining}")
    print(
        json.dumps(
            {
                "status": "read_only_hardened",
                "entities": len(entities),
                "buttons_disabled": len(
                    [
                        item
                        for item in registry_entities()
                        if item["entity_id"].startswith("button.")
                        and item.get("disabled_by") == "user"
                    ]
                ),
                "assist_exposed": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
