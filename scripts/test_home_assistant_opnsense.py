#!/usr/bin/env python3
"""Verify the live OPNsense telemetry entities in Home Assistant."""

from __future__ import annotations

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


def state(token: str, entity_id: str) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    token = access_token()
    feed = state(token, "sensor.muse_opnsense_gateway_feed")
    normalized = state(token, "sensor.muse_internet_status")
    stale = state(token, "binary_sensor.muse_opnsense_data_stale")

    if feed["state"] != "ok":
        raise RuntimeError(f"OPNsense feed is not healthy: {feed['state']}")
    gateways = feed["attributes"].get("gateways", [])
    if not gateways or any("name" not in gateway for gateway in gateways):
        raise RuntimeError("OPNsense gateway feed has no valid gateway")
    if normalized["state"] not in {"normal", "degraded", "offline"}:
        raise RuntimeError(f"Unexpected normalized Internet state: {normalized['state']}")
    if normalized["attributes"].get("credential_role") != "page-muse-readonly":
        raise RuntimeError("Normalized entity does not attest the narrow credential role")
    if normalized["attributes"].get("controls_exposed") not in (False, "False"):
        raise RuntimeError("Normalized Internet entity exposes controls")
    if stale["state"] != "off":
        raise RuntimeError("Fresh OPNsense telemetry is marked stale")

    with open(
        "/config/.storage/core.entity_registry", encoding="utf-8"
    ) as registry_file:
        entities = {
            item["entity_id"]: item
            for item in json.load(registry_file)["data"]["entities"]
        }
    for entity_id in ("sensor.muse_internet_status", "script.muse_narrate_house_status"):
        exposed = (
            entities[entity_id]
            .get("options", {})
            .get("conversation", {})
            .get("should_expose", False)
        )
        if exposed is not True:
            raise RuntimeError(f"Safe narration entity is not exposed: {entity_id}")
    stale_exposed = (
        entities["binary_sensor.muse_opnsense_data_stale"]
        .get("options", {})
        .get("conversation", {})
        .get("should_expose", False)
    )
    if stale_exposed:
        raise RuntimeError("Internal OPNsense stale guard is exposed to Assist")

    print(
        "PASS Home Assistant OPNsense "
        f"gateways={len(gateways)} online={normalized['attributes'].get('online_count')} "
        f"status={normalized['state']} stale={stale['state']} "
        "assist_facts=1 assist_scripts=1 controls=0"
    )


if __name__ == "__main__":
    main()
