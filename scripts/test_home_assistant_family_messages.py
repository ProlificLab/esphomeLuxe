#!/usr/bin/env python3
"""Exercise family-message entities and discard without producing audio."""

from __future__ import annotations

import json
import time
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
    auth = json.load(open("/config/.storage/auth", encoding="utf-8"))
    refresh = next(
        item for item in auth["data"]["refresh_tokens"]
        if item["token_type"] == "normal"
    )
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh["token"],
            "client_id": refresh["client_id"],
        }
    ).encode()
    with urllib.request.urlopen(
        urllib.request.Request(BASE_URL + "/auth/token", data=body), timeout=30
    ) as response:
        return json.load(response)["access_token"]


def state(token: str, entity_id: str) -> str:
    return request(f"/api/states/{entity_id}", token)["state"]


def wait_state(token: str, entity_id: str, expected: str) -> None:
    deadline = time.monotonic() + 10
    while state(token, entity_id) != expected:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"{entity_id} did not become {expected}")
        time.sleep(0.2)


def call(token: str, service: str, data: dict) -> None:
    request(f"/api/services/script/{service}", token, data)


def main() -> None:
    token = access_token()
    current = {item["entity_id"]: item for item in request("/api/states", token)}
    required = {
        "sensor.muse_family_message_queue",
        "script.muse_queue_family_message",
        "script.muse_process_family_message_slot",
        "script.muse_retry_family_message_slot",
        "script.muse_discard_family_message_slot",
    }
    for slot in (1, 2, 3):
        required.update(
            {
                f"input_select.muse_message_slot_{slot}_state",
                f"input_text.muse_message_slot_{slot}_id",
                f"input_text.muse_message_slot_{slot}_text",
                f"input_text.muse_message_slot_{slot}_recipient",
                f"input_text.muse_message_slot_{slot}_target",
                f"input_datetime.muse_message_slot_{slot}_expiry",
                f"input_datetime.muse_message_slot_{slot}_claimed_at",
            }
        )
    if missing := required - current.keys():
        raise RuntimeError(f"Missing family-message entities: {sorted(missing)}")
    delivering = [
        slot for slot in (1, 2, 3)
        if state(token, f"input_select.muse_message_slot_{slot}_state") == "delivering"
    ]
    if delivering:
        raise RuntimeError(f"Refusing to touch uncertain delivering slots: {delivering}")
    test_slot = next(
        (
            slot for slot in (3, 2, 1)
            if state(token, f"input_select.muse_message_slot_{slot}_state") == "empty"
        ),
        None,
    )
    if test_slot is None:
        raise RuntimeError("No empty slot is available for the non-audio test")

    call(token, "muse_set_message_slot_state", {"slot": test_slot, "state": "review"})
    wait_state(token, f"input_select.muse_message_slot_{test_slot}_state", "review")
    call(token, "muse_discard_family_message_slot", {"slot": test_slot})
    wait_state(token, f"input_select.muse_message_slot_{test_slot}_state", "empty")
    for suffix in ("id", "text", "recipient", "target"):
        value = state(token, f"input_text.muse_message_slot_{test_slot}_{suffix}")
        if value not in {"", "unknown"}:
            raise RuntimeError(f"Test slot field was not cleared: {suffix}={value!r}")
    print(f"PASS family message non-audio lifecycle slot={test_slot}")


if __name__ == "__main__":
    main()
