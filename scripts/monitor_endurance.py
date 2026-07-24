#!/usr/bin/env python3
"""Record long-running Muse diagnostics and fail on health regressions."""

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

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
    "voice_no_speech",
    "voice_recoveries",
    "voice_state",
    "voice_timeouts",
    "wifi_signal",
}


def evaluate_samples(
    samples: list[dict], args: argparse.Namespace, device: dict | None = None
) -> dict:
    if not samples:
        raise RuntimeError("Endurance run produced no samples")

    baseline = samples[0]
    final = samples[-1]
    heap_loss = float(baseline["heap_free"]) - float(final["heap_free"])
    psram_loss = float(baseline["free_psram"]) - float(final["free_psram"])
    errors_delta = float(final.get("voice_errors", 0)) - float(
        baseline.get("voice_errors", 0)
    )
    timeouts_delta = float(final.get("voice_timeouts", 0)) - float(
        baseline.get("voice_timeouts", 0)
    )
    no_speech_delta = float(final.get("voice_no_speech", 0)) - float(
        baseline.get("voice_no_speech", 0)
    )
    recoveries_delta = float(final.get("voice_recoveries", 0)) - float(
        baseline.get("voice_recoveries", 0)
    )
    maximum_age = max(float(sample["diagnostic_age_seconds"]) for sample in samples)
    uptime_regressions = sum(
        float(current["uptime"]) < float(previous["uptime"])
        for previous, current in zip(samples, samples[1:])
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
    if no_speech_delta > args.max_new_no_speech:
        failures.append(
            f"new no-speech sessions {no_speech_delta:g} > {args.max_new_no_speech:g}"
        )
    if recoveries_delta > args.max_new_recoveries:
        failures.append(
            f"new voice recoveries {recoveries_delta:g} > {args.max_new_recoveries:g}"
        )
    for label, delta in (
        ("voice errors", errors_delta),
        ("voice timeouts", timeouts_delta),
        ("no-speech sessions", no_speech_delta),
        ("voice recoveries", recoveries_delta),
    ):
        if delta < 0:
            failures.append(f"{label} counter regressed by {-delta:g}")
    if maximum_age > args.max_diagnostic_age:
        failures.append(
            f"diagnostic age {maximum_age:g}s > {args.max_diagnostic_age:g}s"
        )
    if uptime_regressions:
        failures.append(f"uptime regressed {uptime_regressions} time(s)")

    return {
        "schema_version": 2,
        "passed": not failures,
        "device": device or {},
        "started_at": baseline["timestamp"],
        "finished_at": final["timestamp"],
        "observed_duration_seconds": final["elapsed_seconds"],
        "sample_count": len(samples),
        "metrics": {
            "heap_loss": heap_loss,
            "psram_loss": psram_loss,
            "voice_errors_delta": errors_delta,
            "voice_timeouts_delta": timeouts_delta,
            "voice_no_speech_delta": no_speech_delta,
            "voice_recoveries_delta": recoveries_delta,
            "maximum_diagnostic_age_seconds": maximum_age,
            "uptime_regressions": uptime_regressions,
        },
        "thresholds": {
            "max_heap_loss": args.max_heap_loss,
            "max_psram_loss": args.max_psram_loss,
            "max_new_errors": args.max_new_errors,
            "max_new_timeouts": args.max_new_timeouts,
            "max_new_no_speech": args.max_new_no_speech,
            "max_new_recoveries": args.max_new_recoveries,
            "max_diagnostic_age_seconds": args.max_diagnostic_age,
        },
        "failures": failures,
    }


def write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


async def run(args: argparse.Namespace) -> None:
    import yaml
    from aioesphomeapi import APIClient

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Refusing to reuse endurance evidence without --overwrite: {output_path}"
        )

    with open(args.secrets, encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    await client.connect(login=True)
    api_device = await client.device_info()
    device = {
        "host": args.host,
        "name": api_device.name,
        "model": api_device.model,
        "project_name": api_device.project_name,
        "project_version": api_device.project_version,
    }
    entities, _ = await client.list_entities_services()
    object_ids = {entity.key: entity.object_id for entity in entities}
    latest = {}
    heartbeat_updated_at = 0.0
    updated = asyncio.Event()

    def receive_state(state) -> None:
        nonlocal heartbeat_updated_at
        object_id = object_ids.get(state.key)
        if object_id in TRACKED and hasattr(state, "state"):
            latest[object_id] = state.state
            if object_id == "uptime":
                heartbeat_updated_at = time.monotonic()
            updated.set()

    client.subscribe_states(receive_state)
    deadline = time.monotonic() + args.initial_timeout
    required_initial = {
        "free_psram",
        "heap_free",
        "uptime",
        "voice_health",
        "voice_state",
    }
    while not required_initial.issubset(latest):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Initial diagnostics incomplete: {sorted(latest)}")
        updated.clear()
        await asyncio.wait_for(updated.wait(), remaining)

    samples = []
    started = time.monotonic()
    end_at = started + args.duration

    mode = "w" if args.overwrite else "x"
    with output_path.open(mode, encoding="utf-8") as output:
        while True:
            now = time.monotonic()
            sample = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(now - started, 3),
                "diagnostic_age_seconds": round(now - heartbeat_updated_at, 3),
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
            if sample["diagnostic_age_seconds"] > args.max_diagnostic_age:
                break
            await asyncio.sleep(min(args.interval, end_at - now))

    await client.disconnect()
    summary = evaluate_samples(samples, args, device)
    summary_path = args.summary_output or output_path.with_suffix(
        output_path.suffix + ".summary.json"
    )
    write_summary(summary_path, summary)
    metrics = summary["metrics"]

    print(
        f"SUMMARY passed={summary['passed']} samples={summary['sample_count']} "
        f"heap_loss={metrics['heap_loss']:g} psram_loss={metrics['psram_loss']:g} "
        f"errors_delta={metrics['voice_errors_delta']:g} "
        f"timeouts_delta={metrics['voice_timeouts_delta']:g} "
        f"no_speech_delta={metrics['voice_no_speech_delta']:g} "
        f"recoveries_delta={metrics['voice_recoveries_delta']:g} "
        f"max_age={metrics['maximum_diagnostic_age_seconds']:g}s "
        f"output={args.output} summary={summary_path}"
    )
    if summary["failures"]:
        raise RuntimeError("; ".join(summary["failures"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", default="secrets.yaml")
    parser.add_argument("--duration", type=float, default=24 * 60 * 60)
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--initial-timeout", type=float, default=70)
    parser.add_argument("--output", default="release/endurance.jsonl")
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-heap-loss", type=float, default=32768)
    parser.add_argument("--max-psram-loss", type=float, default=131072)
    parser.add_argument("--max-new-errors", type=float, default=0)
    parser.add_argument("--max-new-timeouts", type=float, default=0)
    parser.add_argument("--max-new-no-speech", type=float, default=3)
    parser.add_argument("--max-new-recoveries", type=float, default=0)
    parser.add_argument("--max-diagnostic-age", type=float, default=180)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
