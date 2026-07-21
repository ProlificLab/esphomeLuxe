#!/usr/bin/env python3
"""Report Assist STT/TTS capabilities without exposing Home Assistant secrets."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"


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


async def request(websocket, message_id: int, message_type: str, **data):
    await websocket.send_json({"id": message_id, "type": message_type, **data})
    response = await websocket.receive_json()
    if not response.get("success"):
        raise RuntimeError(f"WebSocket request failed: {message_type}: {response}")
    return response["result"]


async def inspect(token: str) -> dict:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BASE_URL + "/api/websocket") as websocket:
            if (await websocket.receive_json()).get("type") != "auth_required":
                raise RuntimeError("Unexpected Home Assistant WebSocket greeting")
            await websocket.send_json({"type": "auth", "access_token": token})
            if (await websocket.receive_json()).get("type") != "auth_ok":
                raise RuntimeError("Home Assistant WebSocket authentication failed")

            stt = await request(websocket, 1, "stt/engine/list")
            tts = await request(websocket, 2, "tts/engine/list")
            piper = await request(
                websocket, 3, "tts/engine/get", engine_id="tts.piper"
            )
            voices = {}
            for message_id, language in enumerate(("fr_FR", "en_US"), start=4):
                voices[language] = await request(
                    websocket,
                    message_id,
                    "tts/engine/voices",
                    engine_id="tts.piper",
                    language=language,
                )
            return {"stt": stt, "tts": tts, "piper": piper, "voices": voices}


def main() -> None:
    print(json.dumps(asyncio.run(inspect(access_token())), ensure_ascii=False))


if __name__ == "__main__":
    main()
