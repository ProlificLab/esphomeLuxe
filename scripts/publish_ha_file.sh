#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
SOURCE="${1:?Usage: publish_ha_file.sh SOURCE RELATIVE_WWW_PATH}"
REMOTE_PATH="${2:?Usage: publish_ha_file.sh SOURCE RELATIVE_WWW_PATH}"
DESTINATION_ROOT="${HA_DESTINATION_ROOT:-/config/www}"

if [[ ! -f "$SOURCE" ]]; then
  echo "Source file not found: $SOURCE" >&2
  exit 2
fi
if [[ ! "$REMOTE_PATH" =~ ^[A-Za-z0-9._/-]+$ || "$REMOTE_PATH" == /* || "$REMOTE_PATH" == *..* ]]; then
  echo "Unsafe Home Assistant www path: $REMOTE_PATH" >&2
  exit 2
fi
if [[ "$DESTINATION_ROOT" != "/config/www" &&
      "$DESTINATION_ROOT" != "/config/packages" &&
      "$DESTINATION_ROOT" != "/config/custom_sentences" &&
      "$DESTINATION_ROOT" != "/config/muse-tests" ]]; then
  echo "Unsafe Home Assistant destination root: $DESTINATION_ROOT" >&2
  exit 2
fi

destination="$DESTINATION_ROOT/$REMOTE_PATH"
encoded="${destination}.b64"

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

if command -v shasum >/dev/null 2>&1; then
  sha256="$(shasum -a 256 "$SOURCE" | awk '{print $1}')"
else
  sha256="$(sha256sum "$SOURCE" | awk '{print $1}')"
fi

guest_exec docker exec homeassistant mkdir -p "$(dirname "$destination")" >/dev/null
guest_exec docker exec homeassistant sh -c "'rm -f ${encoded} ${encoded}.part.*'" >/dev/null

index=0
while IFS= read -r chunk || [[ -n "$chunk" ]]; do
  printf -v part '%s.part.%04d' "$encoded" "$index"
  guest_exec docker exec homeassistant sh -c \
    "'printf %s $chunk > $part'" >/dev/null
  index=$((index + 1))
done < <(base64 < "$SOURCE" | tr -d '\n' | fold -w 40000)

guest_exec docker exec homeassistant sh -c \
  "'count=\$(ls ${encoded}.part.* 2>/dev/null | wc -l); test \"\$count\" -eq $index && cat ${encoded}.part.* > $encoded && base64 -d $encoded > $destination && echo \"$sha256  $destination\" | sha256sum -c - && rm -f $encoded ${encoded}.part.*'" >/dev/null

if [[ "$DESTINATION_ROOT" == "/config/www" ]]; then
  display_path="/local/$REMOTE_PATH"
else
  display_path="$destination"
fi
printf 'Published %s to %s (SHA256 %s)\n' "$SOURCE" "$display_path" "$sha256"
