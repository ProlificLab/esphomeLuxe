#!/usr/bin/env python3
"""Require an exact firmware version and healthy idle state after OTA."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import time
from typing import Any


def validate_observation(
    project_version: str, expected_version: str, states: dict[str, object]
) -> None:
    if project_version != expected_version:
        raise RuntimeError(
            f"Firmware version mismatch: expected={expected_version} actual={project_version}"
        )
    expected = {"voice_state": "waiting", "voice_health": "healthy"}
    mismatches = {
        name: (states.get(name), value)
        for name, value in expected.items()
        if states.get(name) != value
    }
    if mismatches:
        raise RuntimeError(f"Canary did not return healthy and waiting: {mismatches}")
    if states.get("last_voice_error") not in (None, ""):
        raise RuntimeError(f"Canary reports a voice error: {states['last_voice_error']}")


async def connect(host: str, key: str, timeout: float) -> Any:
    from aioesphomeapi import APIClient

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        client = APIClient(host, 6053, "", noise_psk=key)
        try:
            await client.connect(login=True)
            return client
        except Exception as error:  # The OTA reboot intentionally breaks connectivity.
            last_error = error
            try:
                await client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(1)
    raise TimeoutError(f"Encrypted ESPHome API did not return: {last_error}")


async def observe(client: Any, timeout: float) -> dict[str, object]:
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    wanted = {"voice_state", "voice_health", "last_voice_error"}
    available = set(object_ids.values())
    if not wanted.issubset(available):
        raise RuntimeError(f"Required diagnostics are missing: {sorted(wanted - available)}")
    states: dict[str, object] = {}
    changed = asyncio.Event()

    def receive_state(state: object) -> None:
        object_id = object_ids.get(getattr(state, "key", None))
        if object_id in wanted and hasattr(state, "state"):
            states[object_id] = getattr(state, "state")
            changed.set()

    client.subscribe_states(receive_state)
    deadline = time.monotonic() + timeout
    while not wanted.issubset(states):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Voice diagnostics remained incomplete: {states}")
        changed.clear()
        await asyncio.wait_for(changed.wait(), remaining)
    return states


async def run(args: argparse.Namespace) -> None:
    import yaml

    secrets = yaml.safe_load(args.secrets.read_text(encoding="utf-8"))
    key = secrets.get("api_encryption_key") if isinstance(secrets, dict) else None
    if not isinstance(key, str) or not key:
        raise RuntimeError("api_encryption_key is missing")

    client = await connect(args.host, key, args.reconnect_timeout)
    try:
        info = await client.device_info()
        states = await observe(client, args.state_timeout)
        validate_observation(info.project_version, args.expected_version, states)
        print(
            "PASS exact canary boot "
            f"version={info.project_version} state={states['voice_state']} "
            f"health={states['voice_health']}"
        )
    finally:
        await client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--secrets", type=Path, default=Path("secrets.yaml"))
    parser.add_argument("--reconnect-timeout", type=float, default=90)
    parser.add_argument("--state-timeout", type=float, default=35)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
