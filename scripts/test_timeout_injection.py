#!/usr/bin/env python3
"""Verify the bounded voice-timeout diagnostic path over encrypted API."""

import argparse
import asyncio
import time

import yaml
from aioesphomeapi import APIClient, ButtonInfo


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    button = next(
        entity
        for entity in entities
        if isinstance(entity, ButtonInfo) and entity.object_id == "inject_voice_timeout"
    )
    latest = {}
    updated = asyncio.Event()

    def receive_state(state) -> None:
        object_id = object_ids.get(state.key)
        if object_id and hasattr(state, "state"):
            latest[object_id] = state.state
            updated.set()

    client.subscribe_states(receive_state)

    async def wait_until(predicate, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Condition not met; latest states: {latest}")
            updated.clear()
            await asyncio.wait_for(updated.wait(), remaining)

    await wait_until(
        lambda: latest.get("voice_state") == "waiting"
        and "voice_timeouts" in latest
        and "voice_recoveries" in latest,
        args.initial_timeout,
    )
    timeout_before = float(latest["voice_timeouts"])
    recovery_before = float(latest["voice_recoveries"])

    client.button_command(button.key)
    await wait_until(
        lambda: float(latest.get("voice_timeouts", timeout_before))
        == timeout_before + 1
        and float(latest.get("voice_recoveries", recovery_before))
        == recovery_before + 1
        and latest.get("last_recovery_reason") == "voice_timeout"
        and latest.get("voice_state") == "waiting"
        and latest.get("voice_health") == "healthy",
        args.recovery_timeout,
    )
    info = await client.device_info()
    await client.disconnect()
    print(
        f"PASS version={info.project_version} timeouts={timeout_before:g}->"
        f"{timeout_before + 1:g} recoveries={recovery_before:g}->"
        f"{recovery_before + 1:g} reason=voice_timeout state=waiting health=healthy"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--initial-timeout", type=float, default=15)
    parser.add_argument("--recovery-timeout", type=float, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
