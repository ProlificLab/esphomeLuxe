#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

: "${PVE_HOST:?Set PVE_HOST to an administrative SSH endpoint}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
FRIGATE_HOST="${FRIGATE_HOST:-chris@192.168.1.20}"
FRIGATE_URL="${FRIGATE_URL:-http://192.168.1.20:8971}"
KEYCHAIN_SERVICE="Frigate Home Assistant Viewer"
INTEGRATION_VERSION="5.15.4"
INTEGRATION_COMMIT="7c5aea2d46d5d3c96a6adce57e0b71c42ccfba25"
INTEGRATION_SHA256="deab640ef1c50c74db4ba4879694daf6941fc587c2a6109d43e6cfea1be62f2a"
INTEGRATION_URL="https://api.github.com/repos/blakeblackshear/frigate-hass-integration/tarball/v5.15.4"

guest_exec() {
  local command output
  printf -v command '%q ' "$@"
  output="$(ssh -n -i "$SSH_KEY" -o ConnectTimeout=10 "$PVE_HOST" \
    "sudo -n /usr/sbin/qm guest exec $HA_VM_ID -- $command")"
  jq -e '.exitcode == 0' >/dev/null <<<"$output"
  printf '%s\n' "$output"
}

send_guest_secret() {
  local value="$1"
  local destination="$2"
  printf '%s' "$value" | ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$PVE_HOST" \
    "sudo -n /usr/sbin/qm guest exec $HA_VM_ID --pass-stdin 1 -- \
    docker exec -i homeassistant sh -c 'umask 077; cat > $destination'" >/dev/null
}

wait_for_ha() {
  local attempt
  for attempt in {1..90}; do
    if curl --silent --fail --max-time 3 http://192.168.1.59:8123/ >/dev/null; then
      return 0
    fi
    sleep 2
  done
  echo "Home Assistant did not return after restart" >&2
  return 1
}

scp -q -i "$SSH_KEY" -o IdentitiesOnly=yes \
  "$ROOT_DIR/frigate/provision_viewer.py" "$FRIGATE_HOST:/tmp/muse-provision-viewer.py"
ssh -n -i "$SSH_KEY" -o IdentitiesOnly=yes "$FRIGATE_HOST" \
  "sudo -n install -m 0700 /tmp/muse-provision-viewer.py \
   /opt/frigate/config/muse-provision-viewer.py"

rotate_arg=""
if password="$(security find-generic-password -w -s "$KEYCHAIN_SERVICE" 2>/dev/null)"; then
  :
else
  password="$(openssl rand -base64 48 | tr -d '\n')"
  rotate_arg="--rotate"
fi
trap 'password=""; test -z "${archive:-}" || rm -f "$archive"' EXIT
viewer_result="$(printf '%s' "$password" | \
  ssh -i "$SSH_KEY" -o IdentitiesOnly=yes "$FRIGATE_HOST" \
  "sudo -n docker exec -i frigate python3 /config/muse-provision-viewer.py $rotate_arg")"
jq -e '.role == "viewer" and (.status | IN("configured", "rotated", "role_repaired", "already_configured"))' \
  >/dev/null <<<"$viewer_result"
security add-generic-password -U -a homeassistant_muse \
  -s "$KEYCHAIN_SERVICE" -w "$password" >/dev/null
FRIGATE_URL="$FRIGATE_URL" "$SCRIPT_DIR/test_frigate_viewer.sh"

archive="$(mktemp /tmp/frigate-hass-v5.15.4.XXXXXX)"
curl --fail --silent --show-error --location "$INTEGRATION_URL" -o "$archive"
echo "$INTEGRATION_SHA256  $archive" | shasum -a 256 -c - >/dev/null

for helper in install_frigate_integration.py configure_frigate_integration.py \
  harden_frigate_readonly.py test_home_assistant_frigate.py; do
  PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
    HA_DESTINATION_ROOT=/config/muse-tests \
    "$SCRIPT_DIR/publish_ha_file.sh" "$SCRIPT_DIR/$helper" "$helper" >/dev/null
done
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/muse-tests \
  "$SCRIPT_DIR/publish_ha_file.sh" "$archive" \
  "frigate-hass-v${INTEGRATION_VERSION}.tar.gz" >/dev/null

install_result="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/install_frigate_integration.py \
  --archive "/config/muse-tests/frigate-hass-v${INTEGRATION_VERSION}.tar.gz" \
  --version "$INTEGRATION_VERSION" --commit "$INTEGRATION_COMMIT")"
printf '%s\n' "$install_result" | jq -r '."out-data" // empty'

guest_exec ha core check >/dev/null
guest_exec sh -c "nohup ha core restart >/tmp/muse-ha-restart.log 2>&1 </dev/null &" \
  >/dev/null
wait_for_ha
sleep 20

send_guest_secret "$password" /config/.frigate-viewer-password
password=""
configure_result="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/configure_frigate_integration.py \
  --url "$FRIGATE_URL" --username homeassistant_muse \
  --password-file /config/.frigate-viewer-password)"
printf '%s\n' "$configure_result" | jq -r '."out-data" // empty'
sleep 45

hardening="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/harden_frigate_readonly.py)"
printf '%s\n' "$hardening" | jq -r '."out-data" // empty'
test_result="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/test_home_assistant_frigate.py)"
printf '%s\n' "$test_result" | jq -r '."out-data" // empty'
echo "Frigate authenticated read-only integration provisioning passed."
