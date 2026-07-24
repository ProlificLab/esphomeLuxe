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

sed 's/updates | min/updates | max/' "$PACKAGE" \
  > "$TEMP_DIR/newest-masks-stale.yaml"
if "$SCRIPT_DIR/check_house_intelligence_safety.sh" \
  "$TEMP_DIR/newest-masks-stale.yaml" >/dev/null 2>&1; then
  echo "House-intelligence guard accepted newest-only freshness." >&2
  exit 1
fi

sed 's/oldest > 300/oldest > 3600/' "$PACKAGE" \
  > "$TEMP_DIR/inflated-threshold.yaml"
if "$SCRIPT_DIR/check_house_intelligence_safety.sh" \
  "$TEMP_DIR/inflated-threshold.yaml" >/dev/null 2>&1; then
  echo "House-intelligence guard accepted an inflated stale threshold." >&2
  exit 1
fi

awk 'BEGIN { removed=0 } !removed && /{% endif %}/ { removed=1; next } { print }' \
  "$PACKAGE" > "$TEMP_DIR/unbalanced-template.yaml"
if "$SCRIPT_DIR/check_house_intelligence_safety.sh" \
  "$TEMP_DIR/unbalanced-template.yaml" >/dev/null 2>&1; then
  echo "House-intelligence guard accepted an unbalanced Jinja template." >&2
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
