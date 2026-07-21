#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
FIRMWARE="${1:-.esphome/build/muse-luxe/.pioenvs/muse-luxe/firmware.ota.bin}"
MANIFEST="${2:-manifest_update.json}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  "$SCRIPT_DIR/publish_ha_file.sh" "$FIRMWARE" muse-luxe/firmware.ota.bin
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  "$SCRIPT_DIR/publish_ha_file.sh" "$MANIFEST" muse-luxe/manifest.json

echo "Published firmware and manifest to Home Assistant /local/muse-luxe/."
