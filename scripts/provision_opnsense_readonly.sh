#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

: "${PVE_HOST:?Set PVE_HOST to an administrative SSH endpoint}"

OPNSENSE_HOST="${OPNSENSE_HOST:-root@192.168.1.1}"
OPNSENSE_URL="${OPNSENSE_URL:-https://10.10.30.1}"
HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
KEYCHAIN_KEY_SERVICE="OPNsense Home Assistant API Key"
KEYCHAIN_SECRET_SERVICE="OPNsense Home Assistant API Secret"
CONTROLLER_DIR="/usr/local/opnsense/mvc/app/controllers/OPNsense/Muse/Api"
ACL_DIR="/usr/local/opnsense/mvc/app/models/OPNsense/Muse/ACL"

guest_exec() {
  local output
  output="$(ssh -n -i "$SSH_KEY" -o ConnectTimeout=10 "$PVE_HOST" \
    "sudo -n /usr/sbin/qm guest exec $HA_VM_ID -- $*")"
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

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
ssh -o BatchMode=yes "$OPNSENSE_HOST" \
  "cp /conf/config.xml /conf/config.xml.pre-muse-readonly-$timestamp && \
   mkdir -p '$CONTROLLER_DIR' '$ACL_DIR'"
scp -q \
  "$ROOT_DIR/opnsense/muse-readonly/controllers/OPNsense/Muse/Api/StatusController.php" \
  "$OPNSENSE_HOST:/tmp/MuseStatusController.php"
scp -q \
  "$ROOT_DIR/opnsense/muse-readonly/models/OPNsense/Muse/ACL/ACL.xml" \
  "$OPNSENSE_HOST:/tmp/MuseACL.xml"
scp -q "$ROOT_DIR/opnsense/muse-readonly/provision.php" \
  "$OPNSENSE_HOST:/tmp/muse-provision-readonly.php"
ssh -o BatchMode=yes "$OPNSENSE_HOST" \
	  "install -m 0644 /tmp/MuseStatusController.php '$CONTROLLER_DIR/StatusController.php' && \
	   install -m 0644 /tmp/MuseACL.xml '$ACL_DIR/ACL.xml' && \
	   install -m 0700 /tmp/muse-provision-readonly.php /usr/local/sbin/muse-provision-readonly.php && \
	   rm -f /var/lib/php/tmp/opnsense_acl_cache.json && \
	   rm -f /tmp/MuseStatusController.php /tmp/MuseACL.xml /tmp/muse-provision-readonly.php"

provision_result="$(ssh -o BatchMode=yes "$OPNSENSE_HOST" \
  /usr/local/bin/php /usr/local/sbin/muse-provision-readonly.php)"
status="$(jq -er '.status' <<<"$provision_result")"

api_key=""
api_secret=""
trap 'api_key=""; api_secret=""; provision_result=""' EXIT
if [[ "$status" == "configured" ]]; then
  api_key="$(jq -er '.key' <<<"$provision_result")"
  api_secret="$(jq -er '.secret' <<<"$provision_result")"
  security add-generic-password -U -a homeassistant_muse \
    -s "$KEYCHAIN_KEY_SERVICE" -w "$api_key" >/dev/null
  security add-generic-password -U -a homeassistant_muse \
    -s "$KEYCHAIN_SECRET_SERVICE" -w "$api_secret" >/dev/null
elif [[ "$status" == "already_configured" ]]; then
  api_key="$(security find-generic-password -w -s "$KEYCHAIN_KEY_SERVICE")"
  api_secret="$(security find-generic-password -w -s "$KEYCHAIN_SECRET_SERVICE")"
else
  echo "Unexpected OPNsense provisioning result" >&2
  exit 1
fi
provision_result=""

for _ in {1..20}; do
  if curl --silent --fail --insecure --basic --user "$api_key:$api_secret" \
    "$OPNSENSE_URL/api/muse/status/gateways" | \
    jq -e '.status == "ok" and (.gateways | length) > 0' >/dev/null; then
    break
  fi
  sleep 1
done

PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/muse-tests \
  "$SCRIPT_DIR/publish_ha_file.sh" "$SCRIPT_DIR/configure_opnsense_secrets.py" \
  configure_opnsense_secrets.py >/dev/null
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/muse-tests \
  "$SCRIPT_DIR/publish_ha_file.sh" "$SCRIPT_DIR/test_home_assistant_opnsense.py" \
  test_home_assistant_opnsense.py >/dev/null
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/muse-tests \
  "$SCRIPT_DIR/publish_ha_file.sh" "$SCRIPT_DIR/harden_opnsense_readonly.py" \
  harden_opnsense_readonly.py >/dev/null
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/packages \
  "$SCRIPT_DIR/publish_ha_file.sh" \
  "$ROOT_DIR/home-assistant/packages/muse_house_intelligence.yaml" \
  muse_house_intelligence.yaml >/dev/null

send_guest_secret "$api_key" /config/.opnsense-api-key
send_guest_secret "$api_secret" /config/.opnsense-api-secret
guest_exec docker exec homeassistant python3 \
  /config/muse-tests/configure_opnsense_secrets.py \
  --key-file /config/.opnsense-api-key \
  --secret-file /config/.opnsense-api-secret >/dev/null

guest_exec ha core check >/dev/null
guest_exec sh -c "'nohup ha core restart >/tmp/muse-ha-restart.log 2>&1 </dev/null &'" \
  >/dev/null
for _ in {1..90}; do
  if curl --silent --fail --max-time 3 http://192.168.1.59:8123/ >/dev/null; then
    break
  fi
  sleep 2
done
sleep 35

OPNSENSE_HOST="$OPNSENSE_HOST" OPNSENSE_URL="$OPNSENSE_URL" \
  "$SCRIPT_DIR/test_opnsense_live.sh"
hardening="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/harden_opnsense_readonly.py)"
printf '%s\n' "$hardening" | jq -r '."out-data" // empty'
ha_test="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/test_home_assistant_opnsense.py)"
printf '%s\n' "$ha_test" | jq -r '."out-data" // empty'
echo "OPNsense read-only telemetry provisioning passed; backup suffix $timestamp."
