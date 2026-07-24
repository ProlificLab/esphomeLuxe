#!/usr/bin/env python3
"""Restart Home Assistant and measure Muse voice-client recovery."""

import argparse
import asyncio
import os
import time

import yaml
from aioesphomeapi import APIClient


async def restart_home_assistant(args: argparse.Namespace) -> None:
    command = [
        "ssh",
        "-n",
        "-F",
        "/dev/null",
        "-i",
        os.path.expanduser(args.ssh_key),
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=6",
        args.pve_host,
        "sudo",
        "-n",
        "/usr/sbin/qm",
        "guest",
        "exec",
        str(args.ha_vm_id),
        "--",
        "ha",
        "core",
        "restart",
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), args.ssh_timeout)
    if process.returncode:
        raise RuntimeError(
            f"Home Assistant restart failed ({process.returncode}): "
            f"{stderr.decode().strip() or stdout.decode().strip()}"
        )


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    latest = {}
    state_changed = asyncio.Event()

    def receive_state(state) -> None:
        object_id = object_ids.get(state.key)
        if object_id and hasattr(state, "state"):
            latest[object_id] = state.state
            state_changed.set()

    client.subscribe_states(receive_state)

    async def wait_for_value(object_id: str, value, timeout: float) -> float:
        deadline = time.monotonic() + timeout
        while latest.get(object_id) != value:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"{object_id} did not become {value!r}; "
                    f"last value was {latest.get(object_id)!r}"
                )
            state_changed.clear()
            await asyncio.wait_for(state_changed.wait(), remaining)
        return time.monotonic()

    await wait_for_value("voice_state", "waiting", args.initial_timeout)
    reconnect_before = float(latest.get("voice_reconnects", 0))
    durations = []

    for cycle in range(1, args.cycles + 1):
        started = time.monotonic()
        restart_task = asyncio.create_task(restart_home_assistant(args))
        try:
            offline_at = await wait_for_value(
                "voice_state", "offline", args.offline_timeout
            )
            waiting_at = await wait_for_value(
                "voice_state", "waiting", args.waiting_timeout
            )
            await restart_task
            if args.expect_playing:
                playing_at = await wait_for_value(
                    "voice_state", "playing", args.playing_timeout
                )
                idle_at = await wait_for_value(
                    "voice_state", "waiting", args.announcement_timeout
                )
        except Exception:
            restart_task.cancel()
            await asyncio.gather(restart_task, return_exceptions=True)
            raise
        recovery = waiting_at - offline_at
        total = waiting_at - started
        durations.append(recovery)
        result = "PASS" if recovery <= args.target_recovery else "SLOW"
        print(
            f"{result} cycle={cycle}/{args.cycles} offline_after="
            f"{offline_at - started:.2f}s recovery={recovery:.2f}s total={total:.2f}s",
            flush=True,
        )
        if args.expect_playing:
            print(
                f"PASS announcement playing_after={playing_at - started:.2f}s "
                f"idle_after={idle_at - started:.2f}s",
                flush=True,
            )
        if cycle < args.cycles:
            await asyncio.sleep(args.cooldown)

    reconnect_after = float(latest.get("voice_reconnects", 0))
    health = latest.get("voice_health")
    await client.disconnect()

    slow = [duration for duration in durations if duration > args.target_recovery]
    if slow or health != "healthy":
        raise RuntimeError(
            f"Recovery gate failed: slow={slow}, final health={health!r}"
        )
    if reconnect_after - reconnect_before < args.cycles:
        raise RuntimeError(
            f"Reconnect counter advanced only {reconnect_after - reconnect_before:g} "
            f"times for {args.cycles} restarts"
        )

    print(
        f"SUMMARY cycles={len(durations)} min={min(durations):.2f}s "
        f"max={max(durations):.2f}s average={sum(durations) / len(durations):.2f}s "
        f"reconnects={reconnect_after - reconnect_before:g}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--pve-host", required=True)
    parser.add_argument("--ssh-key", default="~/.ssh/chuwi_pve_ed25519")
    parser.add_argument("--ha-vm-id", type=int, default=120)
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--cooldown", type=float, default=10)
    parser.add_argument("--initial-timeout", type=float, default=10)
    parser.add_argument("--offline-timeout", type=float, default=20)
    parser.add_argument("--waiting-timeout", type=float, default=45)
    parser.add_argument("--target-recovery", type=float, default=10)
    parser.add_argument("--ssh-timeout", type=float, default=30)
    parser.add_argument("--expect-playing", action="store_true")
    parser.add_argument("--playing-timeout", type=float, default=90)
    parser.add_argument("--announcement-timeout", type=float, default=90)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
