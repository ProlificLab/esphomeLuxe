#!/usr/bin/env python3
"""Exercise normal reboot recovery over the encrypted ESPHome API."""

import argparse
import asyncio
import time

import yaml
from aioesphomeapi import APIClient


async def connect(host: str, key: str, timeout: float) -> APIClient:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client = APIClient(host, 6053, "", noise_psk=key)
        try:
            await client.connect(login=True)
            return client
        except Exception:  # The device is expected to refuse connections while booting.
            await asyncio.sleep(0.5)
    raise TimeoutError(f"ESPHome API did not return within {timeout:.0f}s")


async def wait_for_waiting(client: APIClient, timeout: float) -> None:
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    ready = asyncio.Event()

    def receive_state(state) -> None:
        if object_ids.get(state.key) == "voice_state" and state.state == "waiting":
            ready.set()

    client.subscribe_states(receive_state)
    await asyncio.wait_for(ready.wait(), timeout)


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    durations = []
    for cycle in range(1, args.cycles + 1):
        client = await connect(args.host, encryption_key, args.reconnect_timeout)
        entities, _ = await client.list_entities_services()
        restart = next(entity for entity in entities if entity.object_id == "restart")

        started = time.monotonic()
        client.button_command(restart.key)
        await asyncio.sleep(2)

        client = await connect(args.host, encryption_key, args.reconnect_timeout)
        await wait_for_waiting(client, args.waiting_timeout)
        info = await client.device_info()
        duration = time.monotonic() - started
        durations.append(duration)
        result = "PASS" if duration <= args.target_waiting else "SLOW"
        print(
            f"{result} cycle={cycle}/{args.cycles} version={info.project_version} "
            f"waiting_after={duration:.2f}s",
            flush=True,
        )
        await client.disconnect()

        # Safe Mode only marks a boot healthy after 60 seconds.
        if cycle < args.cycles:
            await asyncio.sleep(args.cooldown)

    print(
        f"SUMMARY cycles={len(durations)} min={min(durations):.2f}s "
        f"max={max(durations):.2f}s average={sum(durations) / len(durations):.2f}s"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--cooldown", type=float, default=65)
    parser.add_argument("--reconnect-timeout", type=float, default=30)
    parser.add_argument("--waiting-timeout", type=float, default=35)
    parser.add_argument("--target-waiting", type=float, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
