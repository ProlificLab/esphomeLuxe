#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
FIRMWARE="${1:-.esphome/build/muse-luxe/.pioenvs/muse-luxe/firmware.ota.bin}"
MANIFEST="${2:-manifest_update.json}"

guest_exec() {
  local attempt
  local output
  for attempt in 1 2 3; do
    if output="$(ssh -n -i "$SSH_KEY" \
      -o ConnectTimeout=10 \
      -o ServerAliveInterval=5 \
      -o ServerAliveCountMax=6 \
      "$PVE_HOST" "sudo -n /usr/sbin/qm guest exec $HA_VM_ID -- $*" 2>&1)"; then
      if jq -e '.exitcode == 0' >/dev/null 2>&1 <<<"$output"; then
        printf '%s\n' "$output"
        return 0
      fi
    fi
    printf '%s\n' "$output" >&2
    sleep "$attempt"
  done
  return 1
}

upload_file() {
  local source="$1"
  local destination="$2"
  local encoded="${destination}.b64"
  local index=0
  local part
  local sha256

  if command -v shasum >/dev/null 2>&1; then
    sha256="$(shasum -a 256 "$source" | awk '{print $1}')"
  else
    sha256="$(sha256sum "$source" | awk '{print $1}')"
  fi

  guest_exec docker exec homeassistant sh -c "'rm -f ${encoded} ${encoded}.part.*'"
  while IFS= read -r chunk || [[ -n "$chunk" ]]; do
    printf -v part '%s.part.%04d' "$encoded" "$index"
    guest_exec docker exec homeassistant sh -c \
      "'printf %s $chunk > $part'" >/dev/null
    index=$((index + 1))
  done < <(base64 < "$source" | tr -d '\n' | fold -w 40000)
  guest_exec docker exec homeassistant sh -c \
    "'count=\$(ls ${encoded}.part.* 2>/dev/null | wc -l); test \"\$count\" -eq $index && cat ${encoded}.part.* > $encoded && base64 -d $encoded > $destination && echo \"$sha256  $destination\" | sha256sum -c - && rm -f $encoded ${encoded}.part.*'"
}

guest_exec docker exec homeassistant mkdir -p /config/www/muse-luxe
upload_file "$FIRMWARE" /config/www/muse-luxe/firmware.ota.bin
upload_file "$MANIFEST" /config/www/muse-luxe/manifest.json

echo "Published firmware and manifest to Home Assistant /local/muse-luxe/."
