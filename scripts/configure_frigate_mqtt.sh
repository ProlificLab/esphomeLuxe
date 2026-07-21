#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example root@proxmox-host}"

SSH_KEY="${SSH_KEY:-$HOME/.ssh/chuwi_pve_ed25519}"
HA_VM_ID="${HA_VM_ID:-120}"
FRIGATE_VM_ID="${FRIGATE_VM_ID:-110}"
MQTT_HOST="${MQTT_HOST:-10.10.30.159}"
MQTT_USER="${MQTT_USER:-frigate}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
password="$(openssl rand -hex 24)"

ssh_pve() {
  ssh -n -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$PVE_HOST" "$@"
}

guest_exec() {
  local vm_id="$1"
  shift
  local output
  output="$(ssh_pve "qm guest exec $vm_id -- $*" 2>&1)"
  if ! jq -e '.exitcode == 0' >/dev/null 2>&1 <<<"$output"; then
    printf '%s\n' "$output" >&2
    return 1
  fi
  printf '%s\n' "$output"
}

update_program="$(base64 <<'PY' | tr -d '\n'
import os
from pathlib import Path

root = Path("/opt/frigate")
stamp = os.environ["BACKUP_STAMP"]
user = os.environ["MQTT_USER"]
password = os.environ["MQTT_PASSWORD"]
host = os.environ["MQTT_HOST"]

for relative in (".env", "compose.yaml", "config/config.yml"):
    source = root / relative
    backup = source.with_name(f"{source.name}.pre-mqtt-{stamp}")
    backup.write_bytes(source.read_bytes())

env_path = root / ".env"
env_text = env_path.read_text()
if "FRIGATE_MQTT_PASSWORD=" in env_text:
    raise SystemExit("FRIGATE_MQTT_PASSWORD already exists; refusing to overwrite")
env_path.write_text(
    env_text.rstrip() + f"\nFRIGATE_MQTT_USER={user}\nFRIGATE_MQTT_PASSWORD={password}\n"
)
env_path.chmod(0o600)

compose_path = root / "compose.yaml"
compose = compose_path.read_text()
marker = "    environment:\n"
if marker not in compose or "FRIGATE_MQTT_PASSWORD" in compose:
    raise SystemExit("Unexpected compose environment block")
compose = compose.replace(
    marker,
    marker
    + '      FRIGATE_MQTT_USER: "${FRIGATE_MQTT_USER}"\n'
    + '      FRIGATE_MQTT_PASSWORD: "${FRIGATE_MQTT_PASSWORD}"\n',
    1,
)
compose_path.write_text(compose)

config_path = root / "config/config.yml"
config = config_path.read_text()
old = "mqtt:\n  enabled: false\n"
new = (
    "mqtt:\n"
    "  enabled: true\n"
    f"  host: {host}\n"
    "  user: \"{FRIGATE_MQTT_USER}\"\n"
    "  password: \"{FRIGATE_MQTT_PASSWORD}\"\n"
    "  topic_prefix: frigate\n"
    "  client_id: frigate\n"
)
if config.count(old) != 1:
    raise SystemExit("Unexpected Frigate MQTT block")
config_path.write_text(config.replace(old, new, 1))
PY
)"

guest_exec "$FRIGATE_VM_ID" sh -c \
  "'printf %s $update_program | base64 -d | BACKUP_STAMP=$timestamp MQTT_USER=$MQTT_USER MQTT_PASSWORD=$password MQTT_HOST=$MQTT_HOST python3'" \
  >/dev/null

info="$(ssh_pve "qm guest exec $HA_VM_ID -- docker exec homeassistant sh -c 'curl -fsS -H \"Authorization: Bearer \$SUPERVISOR_TOKEN\" http://supervisor/addons/core_mosquitto/info'")"
options="$(jq -c --arg user "$MQTT_USER" --arg password "$password" \
  '."out-data" | fromjson | .data.options
   | .logins = ((.logins // []) + [{username: $user, password: $password}])
   | {options: .}' <<<"$info")"
options_b64="$(printf '%s' "$options" | base64 | tr -d '\n')"

guest_exec "$HA_VM_ID" docker exec homeassistant sh -c \
  "'printf %s $options_b64 | base64 -d | curl -fsS -H \"Authorization: Bearer \$SUPERVISOR_TOKEN\" -H \"Content-Type: application/json\" --data-binary @- http://supervisor/addons/core_mosquitto/options >/dev/null'" \
  >/dev/null
guest_exec "$HA_VM_ID" ha addons restart core_mosquitto >/dev/null

guest_exec "$FRIGATE_VM_ID" sh -c \
  "'cd /opt/frigate && docker compose up -d'" >/dev/null

for _ in $(seq 1 30); do
  health="$(guest_exec "$FRIGATE_VM_ID" docker inspect -f \
    "'{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}'" \
    frigate | jq -r '."out-data" // empty' | tr -d '\r\n')"
  if [[ "$health" == "healthy" ]]; then
    echo "Frigate MQTT configured; broker and Frigate are healthy."
    echo "Backups use suffix .pre-mqtt-$timestamp on VM $FRIGATE_VM_ID."
    exit 0
  fi
  sleep 2
done

echo "Frigate did not become healthy; restore the .pre-mqtt-$timestamp backups." >&2
exit 1
