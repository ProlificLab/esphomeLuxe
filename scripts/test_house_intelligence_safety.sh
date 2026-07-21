#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PACKAGE="$ROOT_DIR/home-assistant/packages/muse_house_intelligence.yaml"
TEMP_DIR="$(mktemp -d)"

cp "$PACKAGE" "$TEMP_DIR/button.yaml"
printf '\nscript:\n  unsafe:\n    sequence:\n      - action: button.press\n' \
  >> "$TEMP_DIR/button.yaml"
if "$SCRIPT_DIR/check_house_intelligence_safety.sh" \
  "$TEMP_DIR/button.yaml" >/dev/null 2>&1; then
  echo "House-intelligence guard accepted a control button." >&2
  exit 1
fi

cp "$PACKAGE" "$TEMP_DIR/arbitrary-script.yaml"
printf '\nscript:\n  unsafe:\n    sequence:\n      - action: script.shutdown_host\n' \
  >> "$TEMP_DIR/arbitrary-script.yaml"
if "$SCRIPT_DIR/check_house_intelligence_safety.sh" \
  "$TEMP_DIR/arbitrary-script.yaml" >/dev/null 2>&1; then
  echo "House-intelligence guard accepted an arbitrary script." >&2
  exit 1
fi

echo "House-intelligence safety negative fixtures passed."
