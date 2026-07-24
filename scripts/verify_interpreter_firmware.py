#!/usr/bin/env python3
"""Verify that the Muse firmware exposes the interpreter context-reset contract."""

from __future__ import annotations

import json
import time
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


def request(path: str, token: str, *, method: str = "GET"):
    req = urllib.request.Request(
        BASE_URL + path,
        headers={"Authorization": f"Bearer {token}"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main() -> None:
    token = access_token()
    services = request("/api/services", token)
    esphome = next(
        (item["services"] for item in services if item["domain"] == "esphome"),
        {},
    )
    action = "muse_luxe_clear_conversation_context"
    if action not in esphome:
        raise RuntimeError(
            "Muse context-reset API action is unavailable; deploy "
            "hal.9.0-alpha.2 first"
        )

    # A template sensor with update_interval: never has no state until its first
    # publication. Exercise the action once so this preflight proves the full
    # firmware contract instead of relying only on service discovery.
    request(f"/api/services/esphome/{action}", token, method="POST")
    counter = None
    for _ in range(20):
        counter = request(
            "/api/states/sensor.raspiaudio_muse_luxe_voice_context_resets",
            token,
        )
        if counter.get("state") not in {None, "unknown", "unavailable"}:
            break
        time.sleep(0.5)
    if counter is None or counter.get("state") in {None, "unknown", "unavailable"}:
        raise RuntimeError("Muse context-reset action did not publish its counter")
    print(json.dumps({"status": "compatible", "action": action, "counter": counter["state"]}))


if __name__ == "__main__":
    main()
