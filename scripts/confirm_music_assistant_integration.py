"""Confirm the Supervisor-discovered Music Assistant config flow.

Run this inside the Home Assistant Core container. It intentionally refuses
manual and OAuth flows so the Supervisor-owned app token remains the only
credential exchanged with Home Assistant.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
DOMAIN = "music_assistant"
POLL_SECONDS = 2
TIMEOUT_SECONDS = 120


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
    with urllib.request.urlopen(req, timeout=30) as response:
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


async def async_flows_in_progress(token: str) -> list[dict]:
    # aiohttp is part of the Home Assistant Core runtime where this runs.
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BASE_URL + "/api/websocket") as websocket:
            auth_required = await websocket.receive_json()
            if auth_required.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected WebSocket greeting: {auth_required}")
            await websocket.send_json({"type": "auth", "access_token": token})
            auth_result = await websocket.receive_json()
            if auth_result.get("type") != "auth_ok":
                raise RuntimeError(f"Home Assistant authentication failed: {auth_result}")
            await websocket.send_json(
                {"id": 1, "type": "config_entries/flow/progress"}
            )
            result = await websocket.receive_json()
            if not result.get("success"):
                raise RuntimeError(f"Could not list config flows: {result}")
            return result["result"]


def main() -> None:
    if entry := existing_entry():
        print(
            json.dumps(
                {
                    "status": "already_configured",
                    "entry_id": entry["entry_id"],
                    "source": entry["source"],
                }
            )
        )
        return

    token = access_token()
    deadline = time.monotonic() + TIMEOUT_SECONDS
    last_flows: list[dict] = []
    while time.monotonic() < deadline:
        last_flows = asyncio.run(async_flows_in_progress(token))
        candidates = [
            flow
            for flow in last_flows
            if flow.get("handler") == DOMAIN
            and flow.get("context", {}).get("source") == "hassio"
        ]
        if candidates:
            flow = candidates[0]
            if flow.get("step_id") != "hassio_confirm":
                raise RuntimeError(f"Unexpected Music Assistant flow: {flow}")
            result = request(
                f"/api/config/config_entries/flow/{flow['flow_id']}", token, {}
            )
            if result.get("type") not in ("create_entry", "abort"):
                raise RuntimeError(f"Music Assistant confirmation failed: {result}")
            entry = existing_entry()
            if not entry and result.get("type") == "create_entry":
                created = result.get("result", {})
                if created.get("domain") == DOMAIN:
                    entry = created
            if not entry:
                raise RuntimeError(
                    f"Flow completed without a Music Assistant entry: {result}"
                )
            print(
                json.dumps(
                    {
                        "status": result["type"],
                        "entry_id": entry["entry_id"],
                        "source": entry["source"],
                    }
                )
            )
            return
        time.sleep(POLL_SECONDS)

    summary = [
        {
            "handler": flow.get("handler"),
            "step_id": flow.get("step_id"),
            "source": flow.get("context", {}).get("source"),
        }
        for flow in last_flows
    ]
    raise TimeoutError(
        f"No Supervisor Music Assistant confirmation flow after "
        f"{TIMEOUT_SECONDS}s; pending flows: {summary}"
    )


if __name__ == "__main__":
    main()
