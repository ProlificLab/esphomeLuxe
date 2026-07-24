#!/usr/bin/env python3
"""Expose only safe OPNsense facts and narration to Home Assistant Assist."""

from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
EXPOSURE = {
    "sensor.muse_internet_status": True,
    "script.muse_narrate_house_status": True,
    "sensor.muse_opnsense_gateway_feed": False,
    "binary_sensor.muse_opnsense_data_stale": False,
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


def registry() -> dict[str, dict]:
    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        entities = json.load(registry_file)["data"]["entities"]
    return {item["entity_id"]: item for item in entities}


async def apply(token: str, exposure: dict[str, bool]) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BASE_URL + "/api/websocket") as websocket:
            if (await websocket.receive_json()).get("type") != "auth_required":
                raise RuntimeError("Unexpected Home Assistant WebSocket greeting")
            await websocket.send_json({"type": "auth", "access_token": token})
            if (await websocket.receive_json()).get("type") != "auth_ok":
                raise RuntimeError("Home Assistant WebSocket authentication failed")
            for message_id, (entity_id, should_expose) in enumerate(
                exposure.items(), start=1
            ):
                await websocket.send_json(
                    {
                        "id": message_id,
                        "type": "config/entity_registry/update",
                        "entity_id": entity_id,
                        "options_domain": "conversation",
                        "options": {"should_expose": should_expose},
                    }
                )
                result = await websocket.receive_json()
                if not result.get("success"):
                    raise RuntimeError(f"Could not update {entity_id}: {result}")


def main() -> None:
    entities = registry()
    missing = set(EXPOSURE) - set(entities)
    # YAML REST sensors may not enter the registry until their first update.
    missing.discard("sensor.muse_opnsense_gateway_feed")
    if missing:
        raise RuntimeError(f"Required OPNsense narration entities missing: {sorted(missing)}")
    targets = {key: value for key, value in EXPOSURE.items() if key in entities}
    asyncio.run(apply(access_token(), targets))
    mismatches = {}
    for _ in range(20):
        current = registry()
        mismatches = {
            entity_id: current[entity_id]
            .get("options", {})
            .get("conversation", {})
            .get("should_expose", False)
            for entity_id, expected in targets.items()
            if current[entity_id]
            .get("options", {})
            .get("conversation", {})
            .get("should_expose", False)
            is not expected
        }
        if not mismatches:
            break
        time.sleep(0.25)
    if mismatches:
        raise RuntimeError(f"Unexpected Assist exposure state: {mismatches}")
    print("OPNsense Assist exposure hardened: facts=1 narration=1 controls=0")


if __name__ == "__main__":
    main()
