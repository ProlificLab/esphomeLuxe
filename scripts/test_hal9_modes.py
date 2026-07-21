#!/usr/bin/env python3
"""Exercise hal.9 privacy and bounded continuous-conversation modes."""

import argparse
import asyncio
import time

import yaml
from aioesphomeapi import APIClient, SwitchInfo


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    switches = {
        entity.object_id: entity
        for entity in entities
        if isinstance(entity, SwitchInfo)
    }
    required = {"privacy_mode", "continuous_conversation"}
    if not required.issubset(switches):
        raise RuntimeError(f"Missing switches: {sorted(required - switches.keys())}")

    latest = {}
    updated = asyncio.Event()

    def receive_state(state) -> None:
        object_id = object_ids.get(state.key)
        if object_id and hasattr(state, "state"):
            latest[object_id] = state.state
            updated.set()

    client.subscribe_states(receive_state)

    async def wait_until(predicate, label: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{label} not reached; latest={latest}")
            updated.clear()
            await asyncio.wait_for(updated.wait(), remaining)

    await wait_until(
        lambda: latest.get("voice_state") == "waiting"
        and latest.get("voice_health") == "healthy",
        "initial waiting state",
        args.timeout,
    )

    client.switch_command(switches["privacy_mode"].key, True)
    await wait_until(
        lambda: latest.get("privacy_mode") is True
        and latest.get("voice_state") == "privacy"
        and latest.get("voice_health") == "privacy",
        "privacy mode",
        args.timeout,
    )
    print("PASS privacy_on state=privacy health=privacy", flush=True)

    client.switch_command(switches["privacy_mode"].key, False)
    await wait_until(
        lambda: latest.get("privacy_mode") is False
        and latest.get("voice_state") == "waiting"
        and latest.get("voice_health") == "healthy",
        "privacy exit",
        args.timeout,
    )
    print("PASS privacy_off state=waiting health=healthy", flush=True)

    client.switch_command(switches["continuous_conversation"].key, True)
    await wait_until(
        lambda: latest.get("continuous_conversation") is True
        and latest.get("voice_state") == "listening",
        "continuous conversation",
        args.timeout,
    )
    print("PASS continuous_on state=listening", flush=True)

    client.switch_command(switches["continuous_conversation"].key, False)
    await wait_until(
        lambda: latest.get("continuous_conversation") is False
        and latest.get("voice_state") == "waiting"
        and latest.get("voice_health") == "healthy",
        "continuous conversation exit",
        args.timeout,
    )
    info = await client.device_info()
    await client.disconnect()
    print(
        f"PASS continuous_off version={info.project_version} "
        "state=waiting health=healthy"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--timeout", type=float, default=15)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
