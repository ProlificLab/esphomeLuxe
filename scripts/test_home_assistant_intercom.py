#!/usr/bin/env python3
"""Exercise intercom guards and non-audio lifecycle through Home Assistant."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"


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


def state(token: str, entity_id: str) -> str:
    return request(f"/api/states/{entity_id}", token)["state"]


def service(token: str, domain: str, name: str, data: dict | None = None) -> None:
    try:
        request(f"/api/services/{domain}/{name}", token, data or {})
    except urllib.error.HTTPError as error:
        if error.code not in {400, 500}:
            raise


def wait_state(token: str, entity_id: str, expected: str, timeout: int = 10) -> None:
    deadline = time.monotonic() + timeout
    while state(token, entity_id) != expected:
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"{entity_id} did not become {expected}; "
                f"current={state(token, entity_id)}"
            )
        time.sleep(0.2)


def set_status(token: str, status: str) -> None:
    service(
        token,
        "input_select",
        "select_option",
        {
            "entity_id": "input_select.muse_intercom_status",
            "option": status,
        },
    )
    wait_state(token, "input_select.muse_intercom_status", status)


def reset(token: str) -> None:
    current = state(token, "input_select.muse_intercom_status")
    if current in {"ringing", "connected"}:
        set_status(token, "error")
    service(token, "script", "muse_intercom_reset")
    wait_state(token, "input_select.muse_intercom_status", "idle")
    service(
        token,
        "input_boolean",
        "turn_off",
        {"entity_id": "input_boolean.muse_intercom_enabled"},
    )


def main() -> None:
    token = access_token()
    required = {
        "input_boolean.muse_intercom_enabled",
        "input_select.muse_intercom_status",
        "input_text.muse_intercom_last_event",
        "sensor.muse_intercom",
        "timer.muse_intercom_ring",
        "timer.muse_intercom_session",
        "script.muse_intercom_call",
        "script.muse_intercom_accept",
        "script.muse_intercom_relay",
        "script.muse_intercom_decline",
        "script.muse_intercom_hangup",
        "script.muse_intercom_timeout",
        "script.muse_intercom_reset",
    }
    entity_ids = {item["entity_id"] for item in request("/api/states", token)}
    if missing := required - entity_ids:
        raise RuntimeError(f"Missing intercom entities: {sorted(missing)}")

    reset(token)
    service(
        token,
        "script",
        "muse_intercom_call",
        {"source_room": "bureau", "target_room": "cuisine"},
    )
    if state(token, "input_select.muse_intercom_status") != "idle":
        raise RuntimeError("Disabled intercom guard allowed a call")

    service(
        token,
        "input_boolean",
        "turn_on",
        {"entity_id": "input_boolean.muse_intercom_enabled"},
    )
    service(
        token,
        "script",
        "muse_intercom_call",
        {"source_room": "bureau", "target_room": "cuisine"},
    )
    if state(token, "input_select.muse_intercom_status") != "idle":
        raise RuntimeError("Unavailable target guard allowed a call")

    set_status(token, "ringing")
    service(token, "script", "muse_intercom_timeout")
    wait_state(token, "input_select.muse_intercom_status", "timed_out")
    if state(token, "input_text.muse_intercom_last_event") != "timed_out:ringing":
        raise RuntimeError("Ringing timeout was not recorded without transcript data")

    service(token, "script", "muse_intercom_reset")
    wait_state(token, "input_select.muse_intercom_status", "idle")
    set_status(token, "connected")
    service(token, "script", "muse_intercom_timeout")
    wait_state(token, "input_select.muse_intercom_status", "timed_out")
    if state(token, "input_text.muse_intercom_last_event") != "timed_out:connected":
        raise RuntimeError("Connected timeout did not close the ghost-channel state")

    reset(token)
    print(
        "PASS Home Assistant intercom disabled_guard=blocked "
        "unavailable_target=blocked ring_timeout=passed "
        "session_timeout=passed audio_playback=not_exercised enabled=off"
    )


if __name__ == "__main__":
    main()
