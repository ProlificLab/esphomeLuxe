#!/usr/bin/env python3
"""Exercise guarded interactive routines through Home Assistant's REST API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
PLAYER = "media_player.raspiaudio_muse_luxe"


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
    with urllib.request.urlopen(req, timeout=300) as response:
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


def service(token: str, domain: str, name: str, data: dict | None = None):
    return request(f"/api/services/{domain}/{name}", token, data or {})


def conversation(token: str, text: str):
    return request(
        "/api/conversation/process",
        token,
        {
            "text": text,
            "language": "fr",
            "agent_id": "conversation.home_assistant",
        },
    )


def wait_state(token: str, entity_id: str, expected: str, timeout: int = 20) -> None:
    deadline = time.monotonic() + timeout
    while state(token, entity_id) != expected:
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"{entity_id} did not become {expected}; current={state(token, entity_id)}"
            )
        time.sleep(0.25)


def cleanup(token: str) -> None:
    status = state(token, "input_select.muse_routine_status")
    if status in {"running", "paused", "blocked"}:
        service(
            token,
            "input_boolean",
            "turn_on",
            {"entity_id": "input_boolean.muse_routines_enabled"},
        )
        service(token, "script", "muse_cancel_routine")
        status = "cancelled"
    if status in {"idle", "completed", "cancelled"}:
        service(token, "script", "muse_reset_routine")
    service(
        token,
        "input_boolean",
        "turn_off",
        {"entity_id": "input_boolean.muse_routines_enabled"},
    )


def main() -> None:
    token = access_token()
    required = {
        "input_boolean.muse_routines_enabled",
        "input_select.muse_routine_status",
        "input_select.muse_routine_kind",
        "input_select.muse_routine_verification",
        "input_number.muse_routine_step",
        "sensor.muse_interactive_routine",
        "script.muse_start_routine",
        "script.muse_advance_routine",
        "script.muse_pause_routine",
        "script.muse_resume_routine",
        "script.muse_cancel_routine",
        "script.muse_reset_routine",
    }
    entity_ids = {item["entity_id"] for item in request("/api/states", token)}
    if missing := required - entity_ids:
        raise RuntimeError(f"Missing routine entities: {sorted(missing)}")

    cleanup(token)
    try:
        service(
            token,
            "script",
            "muse_start_routine",
            {"routine": "departure", "target": PLAYER},
        )
    except urllib.error.HTTPError:
        pass
    if state(token, "input_select.muse_routine_status") != "idle":
        raise RuntimeError("Disabled routine guard allowed a routine to start")

    try:
        service(token, "input_boolean", "turn_on", {"entity_id": "input_boolean.muse_routines_enabled"})
        service(
            token,
            "script",
            "muse_start_routine",
            {"routine": "departure", "target": PLAYER},
        )
        wait_state(token, "input_select.muse_routine_status", "running")
        if state(token, "input_number.muse_routine_step") != "1.0":
            raise RuntimeError("Routine did not start at step 1")

        service(token, "script", "muse_advance_routine", {"confirmed": False})
        wait_state(token, "input_select.muse_routine_verification", "manual_required")
        if state(token, "input_number.muse_routine_step") != "1.0":
            raise RuntimeError("Unconfirmed manual step advanced")

        service(token, "script", "muse_advance_routine", {"confirmed": True})
        wait_state(token, "input_number.muse_routine_step", "2.0")
        service(token, "script", "muse_pause_routine")
        wait_state(token, "input_select.muse_routine_status", "paused")
        service(token, "script", "muse_resume_routine", {"target": PLAYER})
        wait_state(token, "input_select.muse_routine_status", "running")
        service(token, "script", "muse_cancel_routine")
        wait_state(token, "input_select.muse_routine_status", "cancelled")
        service(token, "script", "muse_reset_routine")
        wait_state(token, "input_select.muse_routine_status", "idle")

        conversation(token, "commence la routine départ")
        wait_state(token, "input_select.muse_routine_status", "running")
        if state(token, "input_select.muse_routine_kind") != "departure":
            raise RuntimeError("Local French start intent selected the wrong routine")
        conversation(token, "mets la routine en pause")
        wait_state(token, "input_select.muse_routine_status", "paused")
        conversation(token, "reprends la routine")
        wait_state(token, "input_select.muse_routine_status", "running")
        conversation(token, "annule la routine")
        wait_state(token, "input_select.muse_routine_status", "cancelled")
        service(token, "script", "muse_reset_routine")

        service(
            token,
            "script",
            "muse_start_routine",
            {"routine": "power_outage", "target": PLAYER},
        )
        service(token, "script", "muse_advance_routine", {"confirmed": False})
        wait_state(token, "input_select.muse_routine_verification", "sensor_verified")
        wait_state(token, "input_number.muse_routine_step", "2.0")
        service(token, "script", "muse_cancel_routine")
        service(token, "script", "muse_reset_routine")
        wait_state(token, "input_select.muse_routine_status", "idle")
    finally:
        cleanup(token)

    print(
        "PASS Home Assistant routines "
        "disabled_guard=blocked manual_guard=blocked pause_resume=passed "
        "local_french_intents=passed victron_sensor_guard=passed "
        "cancel_reset=passed enabled=off"
    )


if __name__ == "__main__":
    main()
