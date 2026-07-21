#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

: "${PVE_HOST:?Set PVE_HOST to an administrative SSH endpoint}"

HA_VM_ID="${HA_VM_ID:-120}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
CREATE_BACKUP="${CREATE_BACKUP:-1}"

guest_exec() {
  local command output
  printf -v command '%q ' "$@"
  output="$(ssh -n -i "$SSH_KEY" -o ConnectTimeout=10 "$PVE_HOST" \
    "sudo -n /usr/sbin/qm guest exec $HA_VM_ID -- $command")"
  if ! jq -e '.exitcode == 0' >/dev/null <<<"$output"; then
    printf '%s\n' "$output" >&2
    return 1
  fi
  printf '%s\n' "$output"
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

for helper in configure_interpreter.py inspect_assist_capabilities.py \
  test_home_assistant_interpreter.py verify_interpreter_firmware.py; do
  PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
    HA_DESTINATION_ROOT=/config/muse-tests \
    "$SCRIPT_DIR/publish_ha_file.sh" "$SCRIPT_DIR/$helper" "$helper" >/dev/null
done

firmware_result="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/verify_interpreter_firmware.py)"
printf '%s\n' "$firmware_result" | jq -r '."out-data" // empty'

if [[ "$CREATE_BACKUP" == "1" ]]; then
  backup_name="pre-muse-interpreter-$(date -u +%Y%m%dT%H%M%SZ)"
  guest_exec ha backups new --name "$backup_name" >/dev/null
  echo "Created Home Assistant backup: $backup_name"
fi

configure_result="$(guest_exec docker exec homeassistant python3 \
  /config/muse-tests/configure_interpreter.py)"
printf '%s\n' "$configure_result" | jq -r '."out-data" // empty'

PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/packages \
  "$SCRIPT_DIR/publish_ha_file.sh" \
  "$ROOT_DIR/home-assistant/packages/muse_interpreter.yaml" \
  muse_interpreter.yaml >/dev/null
PVE_HOST="$PVE_HOST" HA_VM_ID="$HA_VM_ID" SSH_KEY="$SSH_KEY" \
  HA_DESTINATION_ROOT=/config/custom_sentences \
  "$SCRIPT_DIR/publish_ha_file.sh" \
  "$ROOT_DIR/home-assistant/custom_sentences/fr/muse_interpreter.yaml" \
  fr/muse_interpreter.yaml >/dev/null

guest_exec ha core check >/dev/null
guest_exec sh -c "nohup ha core restart >/tmp/muse-ha-restart.log 2>&1 </dev/null &" \
  >/dev/null
wait_for_ha
sleep 30

test_result=""
for attempt in 1 2 3; do
  if test_result="$(guest_exec docker exec homeassistant python3 \
    /config/muse-tests/test_home_assistant_interpreter.py)"; then
    break
  fi
  if [[ "$attempt" == "3" ]]; then
    echo "Interpreter validation did not pass after three attempts" >&2
    exit 1
  fi
  sleep 15
done
printf '%s\n' "$test_result" | jq -r '."out-data" // empty'
echo "Local bounded interpreter provisioning passed."
