#!/usr/bin/env python3
"""Verify authenticated and hardened Frigate entities in Home Assistant."""

from __future__ import annotations

import json
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


def states(token: str) -> dict[str, dict]:
    request = urllib.request.Request(
        BASE_URL + "/api/states", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return {item["entity_id"]: item for item in json.load(response)}


def main() -> None:
    with open(
        "/config/.storage/core.config_entries", encoding="utf-8"
    ) as entries_file:
        entries = json.load(entries_file)["data"]["entries"]
    entry = next((item for item in entries if item["domain"] == "frigate"), None)
    if not entry:
        raise RuntimeError("The official Frigate config entry is missing")
    if entry["data"].get("url") != "http://192.168.1.20:8971":
        raise RuntimeError("Frigate does not use the authenticated port 8971")
    if entry["data"].get("username") != "homeassistant_muse":
        raise RuntimeError("Frigate does not use the dedicated viewer identity")

    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        all_registry = json.load(registry_file)["data"]["entities"]
        registry = [
            item
            for item in all_registry
            if item.get("platform") == "frigate"
        ]
    controls = [
        item["entity_id"]
        for item in registry
        if item["entity_id"].split(".", 1)[0] in CONTROL_DOMAINS
        and item.get("disabled_by") != "user"
    ]
    exposed = [
        item["entity_id"]
        for item in registry
        if item.get("options", {})
        .get("conversation", {})
        .get("should_expose", False)
    ]
    if controls or exposed:
        raise RuntimeError(f"Unsafe Frigate registry state: controls={controls}, exposed={exposed}")

    camera_ids = [
        item["entity_id"]
        for item in registry
        if item["entity_id"].startswith("camera.") and item.get("disabled_by") is None
    ]
    if len(camera_ids) != 11:
        raise RuntimeError(f"Expected exactly 11 Frigate cameras, got {camera_ids}")
    current = states(access_token())
    if "script.muse_narrate_house_status" not in current:
        raise RuntimeError("The combined house narrator script is missing or disabled")
    unavailable = [
        entity_id
        for entity_id in camera_ids
        if current.get(entity_id, {}).get("state") in {None, "unknown", "unavailable"}
    ]
    normalized = current.get("sensor.muse_camera_status")
    if not normalized:
        raise RuntimeError("The normalized camera status sensor is missing")
    if normalized["state"] not in {"normal", "degraded", "offline"}:
        raise RuntimeError(f"Unexpected normalized camera state: {normalized['state']}")
    attributes = normalized["attributes"]
    if int(attributes.get("expected_count", -1)) != 11:
        raise RuntimeError(
            f"Unexpected expected camera count: {attributes.get('expected_count')!r}"
        )
    if attributes.get("online_count") != len(camera_ids) - len(unavailable):
        raise RuntimeError("Normalized camera count disagrees with raw states")
    expected_offline = sorted(entity_id.split(".", 1)[1] for entity_id in unavailable)
    if sorted(attributes.get("offline_cameras", [])) != expected_offline:
        raise RuntimeError("Normalized offline camera list disagrees with raw states")
    if attributes.get("credential_role") != "viewer":
        raise RuntimeError("Normalized camera status does not attest viewer role")
    if attributes.get("controls_exposed") not in (False, "False"):
        raise RuntimeError("Normalized camera status claims controls are exposed")
    source_age = int(attributes.get("source_age_seconds", -1))
    if not 0 <= source_age <= 30:
        raise RuntimeError(f"Frigate source age is not fresh: {source_age}")
    stale = current.get("binary_sensor.muse_frigate_data_stale", {})
    if stale.get("state") != "off":
        raise RuntimeError(
            f"Fresh Frigate data is marked stale: {stale.get('state')!r}"
        )
    normalized_registry = next(
        item
        for item in all_registry
        if item["entity_id"] == "sensor.muse_camera_status"
    )
    if not normalized_registry.get("options", {}).get("conversation", {}).get(
        "should_expose", False
    ):
        raise RuntimeError("Normalized camera status is not exposed to Assist")
    print(
        json.dumps(
            {
                "status": "pass",
                "entry_id": entry["entry_id"],
                "entities": len(registry),
                "cameras": camera_ids,
                "unavailable": unavailable,
                "normalized": normalized["state"],
                "source_age_seconds": source_age,
                "controls_disabled": sum(
                    item["entity_id"].split(".", 1)[0] in CONTROL_DOMAINS
                    for item in registry
                ),
                "assist_exposed": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
