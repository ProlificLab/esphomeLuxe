#!/usr/bin/env python3
"""Disable Frigate controls and hide all raw entities from Assist."""

from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
CONTROL_DOMAINS = {"button", "number", "select", "switch"}


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


def entities() -> list[dict]:
    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        registry = json.load(registry_file)["data"]["entities"]
    return [entity for entity in registry if entity.get("platform") == "frigate"]


def normalized_entity() -> dict | None:
    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        registry = json.load(registry_file)["data"]["entities"]
    return next(
        (entity for entity in registry if entity["entity_id"] == "sensor.muse_camera_status"),
        None,
    )


async def update(token: str, current: list[dict], expose_normalized: bool) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BASE_URL + "/api/websocket") as websocket:
            if (await websocket.receive_json()).get("type") != "auth_required":
                raise RuntimeError("Unexpected Home Assistant WebSocket greeting")
            await websocket.send_json({"type": "auth", "access_token": token})
            if (await websocket.receive_json()).get("type") != "auth_ok":
                raise RuntimeError("Home Assistant WebSocket authentication failed")
            message_id = 0
            for entity in current:
                entity_id = entity["entity_id"]
                domain = entity_id.split(".", 1)[0]
                message_id += 1
                payload = {
                    "id": message_id,
                    "type": "config/entity_registry/update",
                    "entity_id": entity_id,
                    "options_domain": "conversation",
                    "options": {"should_expose": False},
                }
                if domain in CONTROL_DOMAINS:
                    payload["disabled_by"] = "user"
                await websocket.send_json(payload)
                result = await websocket.receive_json()
                if not result.get("success"):
                    raise RuntimeError(f"Could not harden {entity_id}: {result}")
            if expose_normalized:
                message_id += 1
                await websocket.send_json(
                    {
                        "id": message_id,
                        "type": "config/entity_registry/update",
                        "entity_id": "sensor.muse_camera_status",
                        "options_domain": "conversation",
                        "options": {"should_expose": True},
                    }
                )
                result = await websocket.receive_json()
                if not result.get("success"):
                    raise RuntimeError(f"Could not expose normalized camera status: {result}")


def main() -> None:
    current = entities()
    if not current:
        raise RuntimeError("No official Frigate integration entities exist")
    expose_normalized = normalized_entity() is not None
    asyncio.run(update(access_token(), current, expose_normalized))
    for _ in range(40):
        current = entities()
        controls = [
            entity["entity_id"]
            for entity in current
            if entity["entity_id"].split(".", 1)[0] in CONTROL_DOMAINS
            and entity.get("disabled_by") != "user"
        ]
        exposed = [
            entity["entity_id"]
            for entity in current
            if entity.get("options", {})
            .get("conversation", {})
            .get("should_expose", False)
        ]
        normalized = normalized_entity()
        normalized_exposed = bool(
            normalized
            and normalized.get("options", {})
            .get("conversation", {})
            .get("should_expose", False)
        )
        if not controls and not exposed and (
            not expose_normalized or normalized_exposed
        ):
            break
        time.sleep(0.25)
    if controls or exposed or (expose_normalized and not normalized_exposed):
        raise RuntimeError(
            "Frigate hardening incomplete: "
            f"controls={controls}, exposed={exposed}, normalized={normalized_exposed}"
        )
    cameras = [entity for entity in current if entity["entity_id"].startswith("camera.")]
    images = [entity for entity in current if entity["entity_id"].startswith("image.")]
    print(
        json.dumps(
            {
                "status": "read_only_hardened",
                "entities": len(current),
                "controls_disabled": sum(
                    entity["entity_id"].split(".", 1)[0] in CONTROL_DOMAINS
                    for entity in current
                ),
                "assist_exposed": 0,
                "normalized_assist_exposed": int(expose_normalized),
                "cameras": len(cameras),
                "images": len(images),
            }
        )
    )


if __name__ == "__main__":
    main()
