#!/usr/bin/env python3
"""Exercise repeated network announcements through the ESPHome media player."""

import argparse
import asyncio
import statistics
import time

import yaml
from aioesphomeapi import (
    APIClient,
    MediaPlayerEntityState,
    MediaPlayerInfo,
    MediaPlayerState,
    SensorState,
    TextSensorState,
)


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    media = next(entity for entity in entities if isinstance(entity, MediaPlayerInfo))
    object_ids = {entity.key: entity.object_id for entity in entities}

    playing = asyncio.Event()
    idle = asyncio.Event()
    saw_playing = False
    latest = {}
    memory_seen = set()
    fresh_memory = asyncio.Event()

    def receive_state(state) -> None:
        nonlocal saw_playing
        object_id = object_ids.get(state.key)
        if isinstance(state, MediaPlayerEntityState) and state.key == media.key:
            if state.state in (MediaPlayerState.PLAYING, MediaPlayerState.ANNOUNCING):
                saw_playing = True
                playing.set()
            elif state.state == MediaPlayerState.IDLE and saw_playing:
                idle.set()
        elif isinstance(state, (SensorState, TextSensorState)) and object_id:
            latest[object_id] = state.state
            if object_id in ("heap_free", "free_psram"):
                memory_seen.add(object_id)
                if len(memory_seen) == 2:
                    fresh_memory.set()

    client.subscribe_states(receive_state)
    await asyncio.sleep(1)
    memory_before = {
        "heap_free": latest.get("heap_free"),
        "free_psram": latest.get("free_psram"),
    }

    durations = []
    for cycle in range(1, args.cycles + 1):
        playing.clear()
        idle.clear()
        saw_playing = False
        started = time.monotonic()
        client.media_player_command(
            media.key,
            media_url=args.url,
            announcement=True,
        )
        await asyncio.wait_for(playing.wait(), args.start_timeout)
        await asyncio.wait_for(idle.wait(), args.finish_timeout)
        duration = time.monotonic() - started
        durations.append(duration)
        print(
            f"PASS cycle={cycle}/{args.cycles} duration={duration:.2f}s",
            flush=True,
        )
        await asyncio.sleep(args.pause)

    memory_seen.clear()
    fresh_memory.clear()
    await asyncio.wait_for(fresh_memory.wait(), args.memory_timeout)
    memory_after = {
        "heap_free": latest.get("heap_free"),
        "free_psram": latest.get("free_psram"),
    }
    health = latest.get("voice_health")
    voice_state = latest.get("voice_state")
    last_error = latest.get("last_voice_error")
    await client.disconnect()

    if health != "healthy" or voice_state != "waiting" or last_error:
        raise RuntimeError(
            f"Unhealthy final state: health={health!r}, "
            f"voice_state={voice_state!r}, last_error={last_error!r}"
        )

    heap_loss = memory_before["heap_free"] - memory_after["heap_free"]
    psram_loss = memory_before["free_psram"] - memory_after["free_psram"]
    if heap_loss > args.max_heap_loss or psram_loss > args.max_psram_loss:
        raise RuntimeError(
            f"Memory did not recover: heap_loss={heap_loss}, "
            f"psram_loss={psram_loss}"
        )

    print(
        f"SUMMARY cycles={len(durations)} min={min(durations):.2f}s "
        f"max={max(durations):.2f}s average={statistics.mean(durations):.2f}s "
        f"memory_before={memory_before} memory_after={memory_after}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument(
        "--url",
        default="http://10.10.30.159:8123/local/muse-luxe/test-audio.wav",
    )
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--pause", type=float, default=0.5)
    parser.add_argument("--start-timeout", type=float, default=10)
    parser.add_argument("--finish-timeout", type=float, default=15)
    parser.add_argument("--memory-timeout", type=float, default=70)
    parser.add_argument("--max-heap-loss", type=float, default=32768)
    parser.add_argument("--max-psram-loss", type=float, default=131072)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
