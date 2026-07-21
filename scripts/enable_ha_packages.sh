#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
CONFIGURATION="/config/configuration.yaml"

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

current="$(guest_exec docker exec homeassistant cat "$CONFIGURATION" | jq -r '."out-data"')"
if grep -Eq '^[[:space:]]+packages:[[:space:]]*!include_dir_named[[:space:]]+packages' <<<"$current"; then
  echo "Home Assistant packages are already enabled."
elif grep -Eq '^homeassistant:' <<<"$current"; then
  echo "Existing homeassistant block needs a manual packages merge; refusing to edit." >&2
  exit 2
else
  snippet="$(printf '\nhomeassistant:\n  packages: !include_dir_named packages\n' | base64 | tr -d '\n')"
  guest_exec docker exec homeassistant sh -c \
    "'cp $CONFIGURATION ${CONFIGURATION}.pre-muse-packages && printf %s $snippet | base64 -d >> $CONFIGURATION'" \
    >/dev/null
  echo "Enabled !include_dir_named packages in configuration.yaml."
fi

check="$(guest_exec ha core check)"
printf '%s\n' "$check" | jq -r '."out-data" // empty'

if [[ "${RESTART_HA:-0}" == "1" ]]; then
  guest_exec ha core restart >/dev/null
  echo "Home Assistant restart requested."
else
  echo "Configuration is valid. Set RESTART_HA=1 to restart Home Assistant."
fi
