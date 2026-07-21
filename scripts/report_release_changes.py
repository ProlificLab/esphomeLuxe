#!/usr/bin/env python3
"""Generate deterministic release notes and a dependency diff from Git refs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


DEPENDENCY_FILES = (
    ".github/workflows/firmware.yml",
    "luxe_microWW.yaml",
    "luxe_microWW_nabu.yaml",
    "packages/hardware.yaml",
    "scripts/package_firmware.sh",
    "scripts/report_firmware_symbols.sh",
)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], check=check, capture_output=True, text=True
    )
    return result.stdout.strip()


def resolve_ref(ref: str) -> str:
    return git("rev-parse", "--verify", f"{ref}^{{commit}}")


def empty_tree() -> str:
    return git("hash-object", "-t", "tree", "/dev/null")


def automatic_base(target: str) -> tuple[str, str]:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", f"{target}^"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        tag = result.stdout.strip()
        return resolve_ref(tag), tag
    return empty_tree(), "initial release"


def read_at(ref: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else ""


def dependencies_at(ref: str) -> list[dict[str, str]]:
    found: set[tuple[str, str, str]] = set()
    patterns = (
        ("container", re.compile(r"esphome/esphome@sha256:[0-9a-f]{64}")),
        ("esp-idf", re.compile(r"(?m)^\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$")),
        ("esphome-minimum", re.compile(r"(?m)^\s*min_version:\s*([^\s#]+)")),
        ("wake-word", re.compile(r"(?m)^\s*wake_word_model:\s*(\S+)")),
        (
            "github-action",
            re.compile(r"(?m)^\s*-?\s*uses:\s*([^\s#]+@[0-9a-f]{40})"),
        ),
    )
    for path in DEPENDENCY_FILES:
        content = read_at(ref, path)
        for kind, pattern in patterns:
            for match in pattern.finditer(content):
                value = match.group(1) if match.lastindex else match.group(0)
                found.add((kind, value, path))
    return [
        {"kind": kind, "value": value, "source": source}
        for kind, value, source in sorted(found)
    ]


def subsystem(path: str) -> str:
    if path.startswith("home-assistant/"):
        return "home-assistant"
    if path.startswith("packages/") or path.endswith(".yaml"):
        return "firmware"
    if path.startswith("scripts/") or path.startswith(".github/"):
        return "tooling-ci"
    if path.startswith("docs/") or path in {"README.md", "ROADMAP.md"}:
        return "documentation"
    return "other"


def changes_between(base: str, target: str) -> list[dict[str, str]]:
    output = git("diff", "--name-status", "--find-renames", base, target)
    changes = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        path = fields[-1]
        changes.append(
            {"status": status, "path": path, "subsystem": subsystem(path)}
        )
    return changes


def commits_between(base: str, target: str) -> list[dict[str, str]]:
    output = git("log", "--format=%H%x09%s", f"{base}..{target}")
    commits = []
    for line in output.splitlines():
        sha, subject = line.split("\t", 1)
        commits.append({"sha": sha, "short_sha": sha[:7], "subject": subject})
    return commits


def dependency_key(item: dict[str, str]) -> tuple[str, str, str]:
    return item["kind"], item["value"], item["source"]


def build_report(base_arg: str | None, target_arg: str) -> dict[str, object]:
    target = resolve_ref(target_arg)
    if base_arg:
        base = resolve_ref(base_arg)
        base_label = base_arg
    else:
        base, base_label = automatic_base(target)

    before = dependencies_at(base)
    after = dependencies_at(target)
    before_keys = {dependency_key(item): item for item in before}
    after_keys = {dependency_key(item): item for item in after}
    added = [after_keys[key] for key in sorted(after_keys.keys() - before_keys.keys())]
    removed = [before_keys[key] for key in sorted(before_keys.keys() - after_keys.keys())]

    return {
        "schema_version": 1,
        "base": {"label": base_label, "commit": base},
        "target": {"label": target_arg, "commit": target},
        "commits": commits_between(base, target),
        "changes": changes_between(base, target),
        "dependencies": {
            "current": after,
            "added": added,
            "removed": removed,
        },
    }


def markdown(report: dict[str, object]) -> str:
    base = report["base"]
    target = report["target"]
    commits = report["commits"]
    changes = report["changes"]
    dependencies = report["dependencies"]
    lines = [
        "# Release change report",
        "",
        f"- Base: `{base['label']}` (`{base['commit'][:12]}`)",
        f"- Target: `{target['label']}` (`{target['commit'][:12]}`)",
        f"- Commits: {len(commits)}",
        f"- Changed files: {len(changes)}",
        "",
        "## Commits",
        "",
    ]
    lines.extend(
        f"- `{item['short_sha']}` {item['subject']}" for item in commits
    )
    if not commits:
        lines.append("- None")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for change in changes:
        grouped[change["subsystem"]].append(change)
    lines.extend(["", "## Changed subsystems", ""])
    for name in sorted(grouped):
        lines.append(f"### {name}")
        lines.append("")
        lines.extend(
            f"- `{item['status']}` `{item['path']}`" for item in grouped[name]
        )
        lines.append("")
    if not grouped:
        lines.append("- None")
        lines.append("")

    lines.extend(["## Dependency inventory", ""])
    for item in dependencies["current"]:
        lines.append(
            f"- **{item['kind']}** `{item['value']}` from `{item['source']}`"
        )
    if not dependencies["current"]:
        lines.append("- None")

    lines.extend(["", "## Dependency changes", ""])
    for item in dependencies["added"]:
        lines.append(f"- Added **{item['kind']}** `{item['value']}`")
    for item in dependencies["removed"]:
        lines.append(f"- Removed **{item['kind']}** `{item['value']}`")
    if not dependencies["added"] and not dependencies["removed"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Base Git ref; defaults to previous tag")
    parser.add_argument("--target", default="HEAD", help="Target Git ref")
    parser.add_argument(
        "--output-markdown", default="release/CHANGELOG.md", type=Path
    )
    parser.add_argument(
        "--output-json", default="release/dependency-diff.json", type=Path
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args.base, args.target)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.write_text(markdown(report), encoding="utf-8")
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Release report: {args.output_markdown} "
        f"({len(report['commits'])} commits, {len(report['changes'])} files)"
    )


if __name__ == "__main__":
    main()
