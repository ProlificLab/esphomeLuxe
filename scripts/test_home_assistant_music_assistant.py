#!/usr/bin/env python3
"""Exercise the guarded Music Assistant package from Home Assistant Core."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
ANNOUNCEMENT_URL = (
    "http://10.10.30.159:8123/local/muse-luxe/test-audio.wav"
)
PLAYER = "media_player.raspiaudio_muse_luxe_2"
PLAYER_RECOVERY_TIMEOUT = 180


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


def main() -> None:
    token = access_token()
    required = {
        PLAYER,
        "script.muse_music_announcement",
        "script.muse_transfer_audio",
        "script.muse_create_temporary_audio_group",
        "script.muse_close_temporary_audio_group",
        "script.muse_recover_temporary_audio_group",
        "input_boolean.muse_audio_follow_enabled",
        "input_select.muse_audio_group_state",
        "input_text.muse_audio_transfer_status",
        "timer.muse_audio_temporary_group",
    }
    states = request("/api/states", token)
    state_ids = {item["entity_id"] for item in states}
    if missing := required - state_ids:
        raise RuntimeError(f"Missing Music Assistant entities: {sorted(missing)}")
    if state(token, "input_boolean.muse_audio_follow_enabled")["state"] != "off":
        raise RuntimeError("Automatic/manual audio following must default to off")
    if state(token, "input_select.muse_audio_group_state")["state"] != "idle":
        raise RuntimeError("Temporary audio group requires review before testing")
    recovery_deadline = time.monotonic() + PLAYER_RECOVERY_TIMEOUT
    while state(token, PLAYER)["state"] == "unavailable":
        if time.monotonic() >= recovery_deadline:
            raise RuntimeError(
                f"Music Assistant player did not recover in "
                f"{PLAYER_RECOVERY_TIMEOUT}s: {PLAYER}"
            )
        time.sleep(2)

    request(
        "/api/services/script/muse_create_temporary_audio_group",
        token,
        {
            "master": PLAYER,
            "members": [PLAYER],
            "duration_minutes": 5,
        },
    )
    group_guard_deadline = time.monotonic() + 10
    while True:
        group_status = state(token, "input_text.muse_audio_transfer_status")[
            "state"
        ]
        if group_status == "blocked_disabled":
            break
        if time.monotonic() >= group_guard_deadline:
            raise RuntimeError(
                f"Disabled group guard did not run; status={group_status}"
            )
        time.sleep(0.25)
    if state(token, "input_select.muse_audio_group_state")["state"] != "idle":
        raise RuntimeError("Disabled group request claimed persistent state")

    request(
        "/api/services/script/muse_transfer_audio",
        token,
        {
            "source_player": PLAYER,
            "target_player": PLAYER,
            "auto_play": True,
        },
    )
    guard_deadline = time.monotonic() + 10
    while True:
        transfer_status = state(token, "input_text.muse_audio_transfer_status")[
            "state"
        ]
        if transfer_status == "blocked_disabled":
            break
        if time.monotonic() >= guard_deadline:
            raise RuntimeError(
                f"Disabled transfer guard did not run; status={transfer_status}"
            )
        time.sleep(0.25)

    request(
        "/api/services/script/muse_music_announcement",
        token,
        {
            "url": ANNOUNCEMENT_URL,
            "target": PLAYER,
            "volume": 35,
        },
    )
    time.sleep(3)
    final_state = state(token, PLAYER)["state"]
    if final_state == "unavailable":
        raise RuntimeError("Music Assistant player became unavailable after announcement")
    print(
        "PASS Home Assistant Music Assistant "
        f"player={PLAYER} state={final_state} "
        f"transfer_opt_in=off group_guard={group_status} "
        f"transfer_guard={transfer_status}"
    )


if __name__ == "__main__":
    main()
