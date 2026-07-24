#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PACKAGE="$ROOT_DIR/home-assistant/packages/muse_interactive_routines.yaml"
TEMP_DIR="$(mktemp -d)"

expect_rejected() {
  local fixture="$1"
  if "$SCRIPT_DIR/check_routine_safety.sh" "$fixture" >/dev/null 2>&1; then
    echo "Unsafe routine fixture was accepted: $fixture" >&2
    exit 1
  fi
}

cp "$PACKAGE" "$TEMP_DIR/critical-action.yaml"
printf '\nscript:\n  unsafe:\n    sequence:\n      - action: lock.unlock\n' \
  >> "$TEMP_DIR/critical-action.yaml"
expect_rejected "$TEMP_DIR/critical-action.yaml"

cp "$PACKAGE" "$TEMP_DIR/templated-action.yaml"
printf '\nscript:\n  unsafe:\n    sequence:\n      - action: "{{ selected_service }}"\n' \
  >> "$TEMP_DIR/templated-action.yaml"
expect_rejected "$TEMP_DIR/templated-action.yaml"

cp "$PACKAGE" "$TEMP_DIR/unreviewed-script.yaml"
printf '\nscript:\n  unsafe:\n    sequence:\n      - action: script.shutdown_server\n' \
  >> "$TEMP_DIR/unreviewed-script.yaml"
expect_rejected "$TEMP_DIR/unreviewed-script.yaml"

awk 'BEGIN { removed=0 }
  !removed && index($0, "states(target_player) in [\047unknown\047, \047unavailable\047]") {
    removed=1; next
  }
  { print }' "$PACKAGE" > "$TEMP_DIR/start-unavailable.yaml"
expect_rejected "$TEMP_DIR/start-unavailable.yaml"

awk 'BEGIN { removed=0 }
  !removed && index($0, "states(target_player) in [\047unknown\047, \047unavailable\047]") {
    removed=1; next
  }
  { print }' "$TEMP_DIR/start-unavailable.yaml" > "$TEMP_DIR/all-unavailable.yaml"
expect_rejected "$TEMP_DIR/all-unavailable.yaml"

echo "Routine safety negative fixtures passed."
