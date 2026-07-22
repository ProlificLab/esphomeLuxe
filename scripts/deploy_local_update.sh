#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
FIRMWARE="${1:?Usage: deploy_local_update.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256}"
MANIFEST="${2:?Usage: deploy_local_update.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256}"
ENDURANCE_SUMMARY="${3:?Usage: deploy_local_update.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256}"
EXPECTED_SHA256="${4:?Usage: deploy_local_update.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing canary publication from a dirty worktree." >&2
  exit 1
fi

readiness="$(${PYTHON:-python3} "$SCRIPT_DIR/check_canary_deploy_readiness.py" \
  "$FIRMWARE" "$MANIFEST" "$ENDURANCE_SUMMARY" \
  --expected-firmware-sha256 "$EXPECTED_SHA256" --format json)"
firmware_destination="$(${PYTHON:-python3} -c \
  'import json,sys; print(json.load(sys.stdin)["firmware_destination"])' \
  <<<"$readiness")"
manifest_destination="$(${PYTHON:-python3} -c \
  'import json,sys; print(json.load(sys.stdin)["manifest_destination"])' \
  <<<"$readiness")"

PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  "$SCRIPT_DIR/publish_ha_file.sh" "$FIRMWARE" "$firmware_destination"
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  "$SCRIPT_DIR/publish_ha_file.sh" "$MANIFEST" "$manifest_destination"

echo "Published reviewed firmware, then manifest, to the private development channel."
