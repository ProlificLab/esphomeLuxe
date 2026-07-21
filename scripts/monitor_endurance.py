#!/usr/bin/env python3
"""Record long-running Muse diagnostics and fail on health regressions."""

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from aioesphomeapi import APIClient


TRACKED = {
    "free_psram",
    "heap_free",
    "heap_max_block",
    "last_recovery_reason",
    "last_voice_error",
    "loop_time",
    "reset_reason",
    "uptime",
    "voice_errors",
    "voice_health",
    "voice_recoveries",
    "voice_state",
    "voice_timeouts",
    "wifi_signal",
}


async def run(args: argparse.Namespace) -> None:
    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    latest = {}
    updated = asyncio.Event()

    def receive_state(state) -> None:
        object_id = object_ids.get(state.key)
        if object_id in TRACKED and hasattr(state, "state"):
            latest[object_id] = state.state
            updated.set()

    client.subscribe_states(receive_state)
    deadline = time.monotonic() + args.initial_timeout
    while not {"heap_free", "free_psram", "voice_health"}.issubset(latest):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Initial diagnostics incomplete: {sorted(latest)}")
        updated.clear()
        await asyncio.wait_for(updated.wait(), remaining)

    baseline = dict(latest)
    samples = []
    started = time.monotonic()
    end_at = started + args.duration

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as output:
        while True:
            now = time.monotonic()
            sample = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(now - started, 3),
                **latest,
            }
            output.write(json.dumps(sample, sort_keys=True) + "\n")
            output.flush()
            samples.append(sample)
            print(
                f"SAMPLE elapsed={sample['elapsed_seconds']:.0f}s "
                f"health={latest.get('voice_health')} "
                f"state={latest.get('voice_state')} "
                f"heap={latest.get('heap_free')} psram={latest.get('free_psram')}",
                flush=True,
            )
            if now >= end_at:
                break
            await asyncio.sleep(min(args.interval, end_at - now))

    await client.disconnect()

    final = samples[-1]
    heap_loss = float(baseline["heap_free"]) - float(final["heap_free"])
    psram_loss = float(baseline["free_psram"]) - float(final["free_psram"])
    errors_delta = float(final.get("voice_errors", 0)) - float(
        baseline.get("voice_errors", 0)
    )
    timeouts_delta = float(final.get("voice_timeouts", 0)) - float(
        baseline.get("voice_timeouts", 0)
    )

    failures = []
    if final.get("voice_health") != "healthy" or final.get("voice_state") != "waiting":
        failures.append(
            f"final state={final.get('voice_state')!r} health={final.get('voice_health')!r}"
        )
    if heap_loss > args.max_heap_loss:
        failures.append(f"heap loss {heap_loss:g} > {args.max_heap_loss:g}")
    if psram_loss > args.max_psram_loss:
        failures.append(f"PSRAM loss {psram_loss:g} > {args.max_psram_loss:g}")
    if errors_delta > args.max_new_errors:
        failures.append(f"new voice errors {errors_delta:g} > {args.max_new_errors:g}")
    if timeouts_delta > args.max_new_timeouts:
        failures.append(f"new timeouts {timeouts_delta:g} > {args.max_new_timeouts:g}")

    print(
        f"SUMMARY samples={len(samples)} heap_loss={heap_loss:g} "
        f"psram_loss={psram_loss:g} errors_delta={errors_delta:g} "
        f"timeouts_delta={timeouts_delta:g} output={args.output}"
    )
    if failures:
        raise RuntimeError("; ".join(failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--duration", type=float, default=24 * 60 * 60)
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--initial-timeout", type=float, default=70)
    parser.add_argument("--output", default="release/endurance.jsonl")
    parser.add_argument("--max-heap-loss", type=float, default=32768)
    parser.add_argument("--max-psram-loss", type=float, default=131072)
    parser.add_argument("--max-new-errors", type=float, default=0)
    parser.add_argument("--max-new-timeouts", type=float, default=0)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
