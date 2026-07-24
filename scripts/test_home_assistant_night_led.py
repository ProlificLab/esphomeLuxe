#!/usr/bin/env python3
"""Qualify and restore the Home Assistant Muse day/night LED policy."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
NIGHT_MODE = "input_boolean.muse_night_mode"
LED = "light.raspiaudio_muse_luxe"
VOICE_STATE = "sensor.raspiaudio_muse_luxe_voice_state"
VOICE_HEALTH = "sensor.raspiaudio_muse_luxe_voice_health"
ACTIVE_TIMERS = "sensor.raspiaudio_muse_luxe_active_timers"
CONTINUOUS = "switch.raspiaudio_muse_luxe_continuous_conversation"


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


def state(token: str, entity_id: str) -> dict:
    return request(f"/api/states/{entity_id}", token)


def set_night(token: str, enabled: bool) -> None:
    service = "turn_on" if enabled else "turn_off"
    request(
        f"/api/services/input_boolean/{service}",
        token,
        {"entity_id": NIGHT_MODE},
    )


def wait_brightness(token: str, expected_percent: int, timeout: int = 15) -> None:
    deadline = time.monotonic() + timeout
    while True:
        light = state(token, LED)
        brightness = light.get("attributes", {}).get("brightness")
        expected = round(expected_percent * 255 / 100)
        if brightness is not None and abs(int(brightness) - expected) <= 2:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"LED did not reach {expected_percent}%: brightness={brightness}"
            )
        time.sleep(0.25)


def main() -> None:
    token = access_token()
    required = {NIGHT_MODE, LED, VOICE_STATE, VOICE_HEALTH, ACTIVE_TIMERS, CONTINUOUS}
    state_ids = {item["entity_id"] for item in request("/api/states", token)}
    if missing := required - state_ids:
        raise RuntimeError(f"Missing night LED entities: {sorted(missing)}")
    if state(token, VOICE_HEALTH)["state"] != "healthy":
        raise RuntimeError("Muse must be healthy before changing its LED profile")
    if state(token, VOICE_STATE)["state"] != "waiting":
        raise RuntimeError("Muse must be waiting before changing its LED profile")
    if int(float(state(token, ACTIVE_TIMERS)["state"])) != 0:
        raise RuntimeError("Night LED test refuses to run with active timers")
    if state(token, CONTINUOUS)["state"] != "off":
        raise RuntimeError("Night LED test refuses an open continuous conversation")

    original_night = state(token, NIGHT_MODE)["state"] == "on"
    try:
        set_night(token, False)
        wait_brightness(token, 100)
        set_night(token, True)
        wait_brightness(token, 10)
    finally:
        set_night(token, original_night)
        wait_brightness(token, 10 if original_night else 100)
    print(
        "PASS Home Assistant night LED "
        f"day=100 night=10 restored={'night' if original_night else 'day'}"
    )


if __name__ == "__main__":
    main()
