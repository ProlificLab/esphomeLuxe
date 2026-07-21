#!/usr/bin/env python3
"""Verify that privacy mode survives a reboot and can be safely cleared."""

import argparse
import asyncio
import time

import yaml
from aioesphomeapi import APIClient, ButtonInfo, SwitchInfo


async def connect(host: str, key: str, timeout: float) -> APIClient:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client = APIClient(host, 6053, "", noise_psk=key)
        try:
            await client.connect(login=True)
            return client
        except Exception:  # The device is unavailable while rebooting.
            await asyncio.sleep(0.5)
    raise TimeoutError(f"ESPHome API did not return within {timeout:.0f}s")


async def entity_context(client: APIClient):
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    switches = {
        entity.object_id: entity
        for entity in entities
        if isinstance(entity, SwitchInfo)
    }
    buttons = {
        entity.object_id: entity
        for entity in entities
        if isinstance(entity, ButtonInfo)
    }
    return object_ids, switches, buttons


async def wait_for_state(
    client: APIClient,
    object_ids: dict,
    expected: dict,
    timeout: float,
) -> None:
    latest = {}
    changed = asyncio.Event()

    def receive_state(state) -> None:
        object_id = object_ids.get(state.key)
        if object_id and hasattr(state, "state"):
            latest[object_id] = state.state
            changed.set()

    client.subscribe_states(receive_state)
    deadline = time.monotonic() + timeout
    while any(latest.get(name) != value for name, value in expected.items()):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Expected {expected}; latest={latest}")
        changed.clear()
        try:
            await asyncio.wait_for(changed.wait(), remaining)
        except asyncio.TimeoutError as error:
            raise TimeoutError(f"Expected {expected}; latest={latest}") from error


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = await connect(args.host, encryption_key, args.reconnect_timeout)
    object_ids, switches, buttons = await entity_context(client)
    privacy = switches.get("privacy_mode")
    restart = buttons.get("restart")
    if privacy is None or restart is None:
        raise RuntimeError("Required privacy_mode switch or restart button is missing")

    try:
        client.switch_command(privacy.key, True)
        await wait_for_state(
            client,
            object_ids,
            {
                "privacy_mode": True,
                "voice_state": "privacy",
                "voice_health": "privacy",
            },
            args.state_timeout,
        )
        await asyncio.sleep(args.persistence_delay)

        started = time.monotonic()
        client.button_command(restart.key)
        await asyncio.sleep(2)
        client = await connect(args.host, encryption_key, args.reconnect_timeout)
        object_ids, switches, _ = await entity_context(client)
        privacy = switches["privacy_mode"]
        await wait_for_state(
            client,
            object_ids,
            {
                "privacy_mode": True,
                "voice_state": "privacy",
                "voice_health": "privacy",
            },
            args.state_timeout,
        )
        print(
            f"PASS privacy persisted across reboot in {time.monotonic() - started:.2f}s",
            flush=True,
        )
    finally:
        # Never leave the canary muted after a failed or successful test.
        try:
            privacy = switches.get("privacy_mode")
            if privacy is not None:
                client.switch_command(privacy.key, False)
                await wait_for_state(
                    client,
                    object_ids,
                    {
                        "privacy_mode": False,
                        "voice_state": "waiting",
                        "voice_health": "healthy",
                    },
                    args.state_timeout,
                )
                print("PASS privacy cleared state=waiting health=healthy", flush=True)
        finally:
            await client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--reconnect-timeout", type=float, default=35)
    parser.add_argument("--state-timeout", type=float, default=20)
    parser.add_argument("--persistence-delay", type=float, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
