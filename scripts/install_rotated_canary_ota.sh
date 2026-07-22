#!/usr/bin/env bash
set -euo pipefail

usage="Usage: install_rotated_canary_ota.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256 HOST ROTATION_DIR"
FIRMWARE="${1:?$usage}"
MANIFEST="${2:?$usage}"
ENDURANCE_SUMMARY="${3:?$usage}"
EXPECTED_SHA256="${4:?$usage}"
DEVICE_HOST="${5:?$usage}"
ROTATION_DIR="${6:?$usage}"
ACTIVE_SECRETS="${ACTIVE_SECRETS:-secrets.yaml}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

${PYTHON:-python3} "$SCRIPT_DIR/check_secret_rotation_bundle.py" "$ROTATION_DIR" >/dev/null
${PYTHON:-python3} "$SCRIPT_DIR/audit_tracked_secrets.py" \
  --private-secrets "$ROTATION_DIR/secrets.yaml" --require-private-keys 3 >/dev/null
readiness="$(${PYTHON:-python3} "$SCRIPT_DIR/check_canary_deploy_readiness.py" \
  "$FIRMWARE" "$MANIFEST" "$ENDURANCE_SUMMARY" \
  --expected-firmware-sha256 "$EXPECTED_SHA256" --format json)"
version="$(${PYTHON:-python3} -c 'import json,sys; print(json.load(sys.stdin)["version"])' <<<"$readiness")"
sha256="$(${PYTHON:-python3} -c 'import json,sys; print(json.load(sys.stdin)["sha256"])' <<<"$readiness")"
confirmation="ROTATE CANARY $version $sha256"
if [[ -z "${ROTATION_INSTALL_CONFIRM:-}" && -t 0 ]]; then
  printf 'Type exactly: %s\n> ' "$confirmation" >&2
  IFS= read -r ROTATION_INSTALL_CONFIRM
fi
if [[ "${ROTATION_INSTALL_CONFIRM:-}" != "$confirmation" ]]; then
  echo "Rotation installation confirmation is missing or does not match." >&2
  exit 1
fi

OTA_SECRETS="$ROTATION_DIR/transition-ota.yaml" \
VERIFY_SECRETS="$ROTATION_DIR/secrets.yaml" \
CANARY_INSTALL_CONFIRM="INSTALL CANARY $version $sha256" \
  "$SCRIPT_DIR/install_canary_ota.sh" "$FIRMWARE" "$MANIFEST" \
  "$ENDURANCE_SUMMARY" "$EXPECTED_SHA256" "$DEVICE_HOST"

${PYTHON:-python3} "$SCRIPT_DIR/activate_secret_rotation.py" \
  "$ROTATION_DIR" "$ACTIVE_SECRETS"
echo "Rotated canary credentials activated only after exact healthy boot verification."
