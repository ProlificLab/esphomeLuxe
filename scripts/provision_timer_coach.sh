#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_BASE="/config/packages/muse_luxe.yaml"
REMOTE_COACH="/config/packages/muse_timer_coach.yaml"
BASE_BACKUP="${REMOTE_BASE}.pre-timer-coach-${STAMP}"
COACH_BACKUP="${REMOTE_COACH}.pre-timer-coach-${STAMP}"

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

rollback_files() {
  guest_exec docker exec homeassistant sh -c \
    "'if test -e $BASE_BACKUP; then mv $BASE_BACKUP $REMOTE_BASE; else rm -f $REMOTE_BASE; fi; if test -e $COACH_BACKUP; then mv $COACH_BACKUP $REMOTE_COACH; else rm -f $REMOTE_COACH; fi'" \
    >/dev/null
}

guest_exec docker exec homeassistant sh -c \
  "'test ! -e $REMOTE_BASE || cp $REMOTE_BASE $BASE_BACKUP; test ! -e $REMOTE_COACH || cp $REMOTE_COACH $COACH_BACKUP'" \
  >/dev/null

for source in muse_luxe.yaml muse_timer_coach.yaml; do
  if ! PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
    HA_DESTINATION_ROOT=/config/packages \
    "$SCRIPT_DIR/publish_ha_file.sh" \
    "$ROOT_DIR/home-assistant/packages/$source" "$source"; then
    rollback_files
    exit 1
  fi
done

if ! check="$(guest_exec ha core check)"; then
  rollback_files
  echo "Home Assistant validation failed; both timer packages were restored." >&2
  printf '%s\n' "$check" >&2
  exit 1
fi
printf '%s\n' "$check" | jq -r '."out-data" // empty'

if [[ "${RESTART_HA:-0}" == "1" ]]; then
  guest_exec ha core restart >/dev/null
  echo "Home Assistant restart requested; timer checkpoints remain opt-in."
else
  echo "Configuration is valid. Set RESTART_HA=1 during a maintenance window."
fi
