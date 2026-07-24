#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
CONFIGURATION="/config/configuration.yaml"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="${CONFIGURATION}.pre-muse-video-review-${STAMP}"
REMOTE_PACKAGE="/config/packages/muse_video_review.yaml"
REMOTE_DASHBOARD="/config/dashboards/muse-video-review.yaml"
PACKAGE_BACKUP="${REMOTE_PACKAGE}.pre-${STAMP}"
DASHBOARD_BACKUP="${REMOTE_DASHBOARD}.pre-${STAMP}"

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
    "'if test -e $PACKAGE_BACKUP; then mv $PACKAGE_BACKUP $REMOTE_PACKAGE; else rm -f $REMOTE_PACKAGE; fi; if test -e $DASHBOARD_BACKUP; then mv $DASHBOARD_BACKUP $REMOTE_DASHBOARD; else rm -f $REMOTE_DASHBOARD; fi'" \
    >/dev/null
}

current="$(guest_exec docker exec homeassistant cat "$CONFIGURATION" | jq -r '."out-data"')"
changed=0
if grep -Fq "muse-video-review:" <<<"$current"; then
  if ! grep -Fq "filename: dashboards/muse-video-review.yaml" <<<"$current"; then
    echo "Existing Muse dashboard entry has an unexpected filename; refusing." >&2
    exit 2
  fi
  echo "Muse video review dashboard is already registered."
elif grep -Eq '^lovelace:' <<<"$current"; then
  echo "An existing lovelace block needs a manual dashboard merge; refusing." >&2
  exit 2
fi

guest_exec docker exec homeassistant sh -c \
  "'test ! -e $REMOTE_PACKAGE || cp $REMOTE_PACKAGE $PACKAGE_BACKUP; test ! -e $REMOTE_DASHBOARD || cp $REMOTE_DASHBOARD $DASHBOARD_BACKUP'" \
  >/dev/null

if ! PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/packages \
  "$SCRIPT_DIR/publish_ha_file.sh" \
  "$ROOT_DIR/home-assistant/packages/muse_video_review.yaml" \
  muse_video_review.yaml; then
  rollback_files
  exit 1
fi
if ! PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/dashboards \
  "$SCRIPT_DIR/publish_ha_file.sh" \
  "$ROOT_DIR/home-assistant/dashboards/muse-video-review.yaml" \
  muse-video-review.yaml; then
  rollback_files
  exit 1
fi

if ! grep -Fq "muse-video-review:" <<<"$current"; then
  snippet="$(printf '\nlovelace:\n  mode: storage\n  dashboards:\n    muse-video-review:\n      mode: yaml\n      title: Revue video Muse\n      icon: mdi:image-lock-outline\n      show_in_sidebar: true\n      require_admin: false\n      filename: dashboards/muse-video-review.yaml\n' | base64 | tr -d '\n')"
  if ! guest_exec docker exec homeassistant sh -c \
    "'cp $CONFIGURATION $BACKUP && printf %s $snippet | base64 -d >> $CONFIGURATION'" \
    >/dev/null; then
    rollback_files
    exit 1
  fi
  changed=1
  echo "Registered the secondary YAML dashboard; backup: $BACKUP"
fi

if ! check="$(guest_exec ha core check)"; then
  if [[ "$changed" == "1" ]]; then
    guest_exec docker exec homeassistant cp "$BACKUP" "$CONFIGURATION" >/dev/null
  fi
  rollback_files
  echo "Home Assistant validation failed; all changed files were restored." >&2
  printf '%s\n' "$check" >&2
  exit 1
fi
printf '%s\n' "$check" | jq -r '."out-data" // empty'

if [[ "${RESTART_HA:-0}" == "1" ]]; then
  guest_exec ha core restart >/dev/null
  echo "Home Assistant restart requested."
else
  echo "Configuration is valid. Set RESTART_HA=1 during a maintenance window."
fi
