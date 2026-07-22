#!/usr/bin/env python3
"""Fail closed unless a saved GitHub run matches the clean source commit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


TOP_KEYS = {"conclusion", "databaseId", "event", "headSha", "jobs", "name", "status", "url"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def validate(path: Path, expected_commit: str) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", expected_commit) is None:
        fail("Expected source commit is not a full lowercase SHA")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        fail(f"Saved source CI report is invalid: {error}")
    if not isinstance(report, dict) or set(report) != TOP_KEYS:
        fail("Saved source CI report keys differ from schema")
    run_id = report["databaseId"]
    jobs = report["jobs"]
    if type(run_id) is not int or run_id <= 0 or not isinstance(jobs, list):
        fail("Saved source CI run identity is invalid")
    compile_jobs = [job for job in jobs if isinstance(job, dict) and job.get("name") == "compile"]
    if len(compile_jobs) != 1:
        fail("Saved source CI report must contain exactly one compile job")
    job = compile_jobs[0]
    if (
        type(job.get("databaseId")) is not int
        or job["databaseId"] <= 0
        or report["headSha"] != expected_commit
        or report["name"] != "Firmware source validation"
        or report["status"] != "completed"
        or report["conclusion"] != "success"
        or report["event"] not in {"pull_request", "push"}
        or report["url"] != f"https://github.com/ProlificLab/esphomeLuxe/actions/runs/{run_id}"
        or job.get("status") != "completed"
        or job.get("conclusion") != "success"
    ):
        fail("Saved source CI report is not the exact successful source run")
    return {
        "schema_version": 1,
        "passed": True,
        "run_id": run_id,
        "job_id": job["databaseId"],
        "head_sha": expected_commit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ci_json", type=Path)
    parser.add_argument("expected_commit")
    args = parser.parse_args()
    print(json.dumps(validate(args.ci_json, args.expected_commit), sort_keys=True))


if __name__ == "__main__":
    main()
