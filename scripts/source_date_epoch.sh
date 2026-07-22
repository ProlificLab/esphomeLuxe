#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REF="${1:-HEAD}"

commit="$(git -C "$ROOT" rev-parse --verify "$REF^{commit}")"
if [[ ! "$commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Reproducible build commit is not a full lowercase SHA." >&2
  exit 1
fi
epoch="$(git -C "$ROOT" show -s --format=%ct "$commit")"
if [[ ! "$epoch" =~ ^[1-9][0-9]{8,}$ ]]; then
  echo "Reproducible build epoch is invalid." >&2
  exit 1
fi
printf '%s\n' "$epoch"
