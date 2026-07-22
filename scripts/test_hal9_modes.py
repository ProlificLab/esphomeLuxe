#!/usr/bin/env python3
"""Qualify hal.9 privacy and continuous-conversation modes over encrypted API."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time

import yaml
from aioesphomeapi import APIClient, SwitchInfo


MODE_CASES = (
    "privacy_on",
    "privacy_off",
    "continuous_on",
    "continuous_off",
)
DIAGNOSTICS = ("voice_errors", "voice_timeouts", "voice_recoveries")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_evidence(path: Path, evidence: dict, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Evidence already exists: {path}; use --overwrite deliberately"
        )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(evidence, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


async def run(args: argparse.Namespace) -> None:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(
            f"Evidence already exists: {args.output}; use --overwrite deliberately"
        )
    with args.secrets.open(encoding="utf-8") as secrets_file:
        encryption_key = yaml.safe_load(secrets_file)["api_encryption_key"]

    client = APIClient(args.host, 6053, "", noise_psk=encryption_key)
    connected = False
    modes_changed = False
    switches: dict[str, SwitchInfo] = {}
    latest: dict[str, object] = {}
    revisions: dict[str, int] = {}
    updated = asyncio.Event()
    cases: list[dict[str, object]] = []
    started_at = utc_now()
    evidence: dict | None = None

    async def wait_until(predicate, label: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{label} not reached; latest={latest}")
            updated.clear()
            try:
                await asyncio.wait_for(updated.wait(), remaining)
            except asyncio.TimeoutError as error:
                raise TimeoutError(f"{label} not reached; latest={latest}") from error

    def record_case(name: str) -> None:
        cases.append(
            {
                "name": name,
                "observed_at": utc_now(),
                "privacy_mode": bool(latest.get("privacy_mode")),
                "continuous_conversation": bool(
                    latest.get("continuous_conversation")
                ),
                "voice_state": str(latest.get("voice_state", "")),
                "voice_health": str(latest.get("voice_health", "")),
            }
        )
        print(
            f"PASS {name} state={latest.get('voice_state')} "
            f"health={latest.get('voice_health')}",
            flush=True,
        )

    try:
        await client.connect(login=True)
        connected = True
        info = await client.device_info()
        if info.project_version != args.expected_version:
            raise RuntimeError(
                f"Firmware version mismatch: expected={args.expected_version} "
                f"actual={info.project_version}"
            )

        entities, _ = await client.list_entities_services()
        object_ids = {entity.key: entity.object_id for entity in entities}
        switches = {
            entity.object_id: entity
            for entity in entities
            if isinstance(entity, SwitchInfo)
        }
        required_switches = {"privacy_mode", "continuous_conversation"}
        missing = required_switches - switches.keys()
        if missing:
            raise RuntimeError(f"Missing switches: {sorted(missing)}")

        def receive_state(state) -> None:
            object_id = object_ids.get(state.key)
            if object_id and hasattr(state, "state"):
                latest[object_id] = state.state
                revisions[object_id] = revisions.get(object_id, 0) + 1
                updated.set()

        client.subscribe_states(receive_state)
        required_states = {
            "privacy_mode",
            "continuous_conversation",
            "voice_state",
            "voice_health",
            "active_timers",
            *DIAGNOSTICS,
        }
        await wait_until(
            lambda: required_states.issubset(latest),
            "initial diagnostics",
            args.timeout,
        )
        if latest["privacy_mode"] is not False:
            raise RuntimeError("Privacy is already enabled; refusing to change it")
        if latest["continuous_conversation"] is not False:
            raise RuntimeError(
                "Continuous conversation is already enabled; refusing to change it"
            )
        if int(float(latest["active_timers"])) != 0:
            raise RuntimeError("Active timers present; refusing mode qualification")
        if latest["voice_state"] != "waiting" or latest["voice_health"] != "healthy":
            raise RuntimeError(
                "Canary must start healthy and waiting; "
                f"state={latest['voice_state']} health={latest['voice_health']}"
            )
        diagnostics_before = {
            name: float(latest[name]) for name in DIAGNOSTICS
        }

        modes_changed = True
        client.switch_command(switches["privacy_mode"].key, True)
        await wait_until(
            lambda: latest.get("privacy_mode") is True
            and latest.get("voice_state") == "privacy"
            and latest.get("voice_health") == "privacy",
            "privacy mode",
            args.timeout,
        )
        record_case("privacy_on")

        client.switch_command(switches["privacy_mode"].key, False)
        await wait_until(
            lambda: latest.get("privacy_mode") is False
            and latest.get("voice_state") == "waiting"
            and latest.get("voice_health") == "healthy",
            "privacy exit",
            args.timeout,
        )
        record_case("privacy_off")

        client.switch_command(switches["continuous_conversation"].key, True)
        await wait_until(
            lambda: latest.get("continuous_conversation") is True
            and latest.get("voice_state") == "listening"
            and latest.get("voice_health") == "healthy",
            "continuous conversation",
            args.timeout,
        )
        record_case("continuous_on")

        client.switch_command(switches["continuous_conversation"].key, False)
        await wait_until(
            lambda: latest.get("continuous_conversation") is False
            and latest.get("voice_state") == "waiting"
            and latest.get("voice_health") == "healthy",
            "continuous conversation exit",
            args.timeout,
        )
        record_case("continuous_off")

        diagnostics_after = {name: float(latest[name]) for name in DIAGNOSTICS}
        if diagnostics_after != diagnostics_before:
            raise RuntimeError(
                "Voice diagnostic counters changed during qualification: "
                f"before={diagnostics_before} after={diagnostics_after}"
            )
        evidence = {
            "schema_version": 1,
            "passed": True,
            "device": {
                "host": args.host,
                "name": info.name,
                "model": info.model,
                "project_name": info.project_name,
                "project_version": info.project_version,
            },
            "started_at": started_at,
            "cases": cases,
            "diagnostics_before": diagnostics_before,
            "diagnostics_after": diagnostics_after,
        }
    finally:
        if connected:
            try:
                if modes_changed and switches:
                    cleanup_revisions = {
                        name: revisions.get(name, 0)
                        for name in ("continuous_conversation", "privacy_mode")
                    }
                    if evidence is None:
                        client.switch_command(
                            switches["continuous_conversation"].key, False
                        )
                        client.switch_command(switches["privacy_mode"].key, False)
                    await wait_until(
                        lambda: latest.get("continuous_conversation") is False
                        and latest.get("privacy_mode") is False
                        and latest.get("voice_state") == "waiting"
                        and latest.get("voice_health") == "healthy"
                        and (
                            evidence is not None
                            or all(
                                revisions.get(name, 0) > revision
                                for name, revision in cleanup_revisions.items()
                            )
                        ),
                        "safe cleanup",
                        args.cleanup_timeout,
                    )
            finally:
                await client.disconnect()
    if evidence is None:
        raise RuntimeError("Mode qualification completed without evidence")
    evidence["cleanup"] = {
        "observed_at": utc_now(),
        "privacy_mode": latest["privacy_mode"],
        "continuous_conversation": latest["continuous_conversation"],
        "voice_state": latest["voice_state"],
        "voice_health": latest["voice_health"],
    }
    evidence["finished_at"] = utc_now()
    write_evidence(args.output, evidence, args.overwrite)
    print(f"EVIDENCE {args.output}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="10.10.40.100")
    parser.add_argument("--secrets", type=Path, default=Path("secrets.yaml"))
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--cleanup-timeout", type=float, default=30)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
