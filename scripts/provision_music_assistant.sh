#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_PACKAGE="/config/packages/muse_music_assistant.yaml"
BACKUP="${REMOTE_PACKAGE}.pre-audio-groups-${STAMP}"

guest_exec() {
  local output
  output="$(ssh -n -i "$SSH_KEY" \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=6 \
    "$PVE_HOST" "sudo -n /usr/sbin/qm guest exec $HA_VM_ID -- $*" 2>&1)"
  printf '%s\n' "$output"
  jq -e '.exitcode == 0' >/dev/null <<<"$output"
}

rollback_file() {
  guest_exec docker exec homeassistant sh -c \
    "'if test -e $BACKUP; then mv $BACKUP $REMOTE_PACKAGE; else rm -f $REMOTE_PACKAGE; fi'" \
    >/dev/null
}

guest_exec docker exec homeassistant sh -c \
  "'test ! -e $REMOTE_PACKAGE || cp $REMOTE_PACKAGE $BACKUP'" >/dev/null

if ! PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/packages \
  "$SCRIPT_DIR/publish_ha_file.sh" \
  "$ROOT_DIR/home-assistant/packages/muse_music_assistant.yaml" \
  muse_music_assistant.yaml; then
  rollback_file
  exit 1
fi

if ! check="$(guest_exec ha core check)"; then
  rollback_file
  echo "Home Assistant validation failed; the Music Assistant package was restored." >&2
  printf '%s\n' "$check" >&2
  exit 1
fi
printf '%s\n' "$check" | jq -r '."out-data" // empty'

if [[ "${RESTART_HA:-0}" == "1" ]]; then
  guest_exec ha core restart >/dev/null
  echo "Home Assistant restart requested; audio grouping remains opt-in."
else
  echo "Configuration is valid. Set RESTART_HA=1 during a maintenance window."
fi
