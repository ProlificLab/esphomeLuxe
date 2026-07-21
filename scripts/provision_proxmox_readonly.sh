#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

: "${PVE_HOST:?Set PVE_HOST to an administrative SSH endpoint}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
PVE_GROUP="${PVE_GROUP:-homeassistant}"
PVE_USER="${PVE_USER:-homeassistant@pve}"
PVE_TOKEN_ID="${PVE_TOKEN_ID:-homeassistant}"
PVE_TOKEN_FULL_ID="$PVE_USER!$PVE_TOKEN_ID"
PVE_API_HOST="${PVE_API_HOST:-${PVE_HOST#*@}}"
HA_CONFIGURATOR="${HA_CONFIGURATOR:-/config/muse-tests/configure_proxmox_readonly.py}"
HA_HARDENER="${HA_HARDENER:-/config/muse-tests/harden_proxmox_readonly.py}"
SECRET_FILE="/config/.proxmox-homeassistant-token"
KEYCHAIN_SERVICE="Proxmox Home Assistant API"

remote() {
  local command
  printf -v command '%q ' "$@"
  ssh -n -i "$SSH_KEY" -o ConnectTimeout=10 "$PVE_HOST" \
    "sudo -n $command"
}

guest_exec() {
  local output
  output="$(remote /usr/sbin/qm guest exec "$HA_VM_ID" -- "$@")"
  jq -e '.exitcode == 0' >/dev/null <<<"$output"
  printf '%s\n' "$output"
}

groups="$(remote pveum group list --output-format json)"
if ! jq -e --arg group "$PVE_GROUP" '.[] | select(.groupid == $group)' \
  >/dev/null <<<"$groups"; then
  remote pveum group add "$PVE_GROUP" \
    --comment "Read-only monitoring from Home Assistant" >/dev/null
fi

users="$(remote pveum user list --output-format json)"
if ! jq -e --arg user "$PVE_USER" '.[] | select(.userid == $user)' \
  >/dev/null <<<"$users"; then
  remote pveum user add "$PVE_USER" --groups "$PVE_GROUP" \
    --comment "Home Assistant read-only monitoring" >/dev/null
else
  remote pveum user modify "$PVE_USER" --groups "$PVE_GROUP" \
    --enable 1 >/dev/null
fi
remote pveum acl modify / --groups "$PVE_GROUP" --roles PVEAuditor \
  --propagate 1 >/dev/null

entries="$(guest_exec docker exec homeassistant cat \
  /config/.storage/core.config_entries | jq -r '."out-data"')"
configured=0
if jq -e '.data.entries[] | select(.domain == "proxmoxve")' \
  >/dev/null <<<"$entries"; then
  configured=1
fi

tokens="$(remote pveum user token list "$PVE_USER" --output-format json)"
token_exists=0
if jq -e --arg token "$PVE_TOKEN_ID" '.[] | select(.tokenid == $token)' \
  >/dev/null <<<"$tokens"; then
  token_exists=1
fi

if [[ "$configured" == "1" && "$token_exists" == "1" ]]; then
  echo "Proxmox is already configured in Home Assistant; verifying read-only ACL."
elif [[ "$token_exists" == "1" && "${ROTATE_TOKEN:-0}" != "1" ]]; then
  echo "Token exists but Home Assistant is not configured." >&2
  echo "Set ROTATE_TOKEN=1 to revoke and replace it explicitly." >&2
  exit 2
elif [[ "$token_exists" == "1" ]]; then
  remote pveum user token delete "$PVE_USER" "$PVE_TOKEN_ID" >/dev/null
  token_exists=0
fi

token_secret=""
if [[ "$token_exists" == "0" ]]; then
  token_json="$(remote pveum user token add "$PVE_USER" "$PVE_TOKEN_ID" \
    --privsep 1 --comment "Revocable Home Assistant monitoring token" \
    --output-format json)"
  token_secret="$(jq -er '.value' <<<"$token_json")"
fi

remote pveum acl modify / --tokens "$PVE_TOKEN_FULL_ID" \
  --roles PVEAuditor --propagate 1 >/dev/null
permissions="$(remote pveum user token permissions "$PVE_USER" \
  "$PVE_TOKEN_ID" --output-format json)"
printf '%s' "$permissions" | python3 \
  "$SCRIPT_DIR/check_proxmox_permissions.py" >/dev/null

if [[ "$configured" == "0" ]]; then
  guest_exec docker exec homeassistant test -r "$HA_CONFIGURATOR" >/dev/null
  if command -v security >/dev/null 2>&1; then
    security add-generic-password -U -a "$PVE_TOKEN_FULL_ID" \
      -s "$KEYCHAIN_SERVICE" -w "$token_secret" >/dev/null
  fi
  printf '%s' "$token_secret" | ssh -i "$SSH_KEY" -o ConnectTimeout=10 \
    "$PVE_HOST" "sudo -n /usr/sbin/qm guest exec $HA_VM_ID --pass-stdin 1 -- \
    docker exec -i homeassistant sh -c 'umask 077; cat > $SECRET_FILE'" \
    >/dev/null
  token_secret=""
  result="$(guest_exec docker exec homeassistant python3 "$HA_CONFIGURATOR" \
    --host "$PVE_API_HOST" --username "${PVE_USER%@*}" \
    --token-id "$PVE_TOKEN_ID" --secret-file "$SECRET_FILE")"
  printf '%s\n' "$result" | jq -r '."out-data" // empty'
fi

guest_exec docker exec homeassistant test -r "$HA_HARDENER" >/dev/null
hardening="$(guest_exec docker exec homeassistant python3 "$HA_HARDENER")"
printf '%s\n' "$hardening" | jq -r '."out-data" // empty'

echo "Proxmox read-only provisioning passed for $PVE_TOKEN_FULL_ID."
