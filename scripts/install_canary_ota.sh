#!/usr/bin/env bash
set -euo pipefail

usage="Usage: install_canary_ota.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256 HOST"
FIRMWARE="${1:?$usage}"
MANIFEST="${2:?$usage}"
ENDURANCE_SUMMARY="${3:?$usage}"
EXPECTED_SHA256="${4:?$usage}"
DEVICE_HOST="${5:?$usage}"
SECRETS="${SECRETS:-secrets.yaml}"
OTA_SECRETS="${OTA_SECRETS:-$SECRETS}"
VERIFY_SECRETS="${VERIFY_SECRETS:-$SECRETS}"
IMAGE="esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "Refusing canary installation from a dirty worktree." >&2
  exit 1
fi
for secrets_file in "$OTA_SECRETS" "$VERIFY_SECRETS"; do
  if [[ ! -f "$secrets_file" ]]; then
    echo "Secrets file not found: $secrets_file" >&2
    exit 1
  fi
done

readiness="$(${PYTHON:-python3} "$SCRIPT_DIR/check_canary_deploy_readiness.py" \
  "$FIRMWARE" "$MANIFEST" "$ENDURANCE_SUMMARY" \
  --expected-firmware-sha256 "$EXPECTED_SHA256" --format json)"
version="$(${PYTHON:-python3} -c \
  'import json,sys; print(json.load(sys.stdin)["version"])' <<<"$readiness")"
sha256="$(${PYTHON:-python3} -c \
  'import json,sys; print(json.load(sys.stdin)["sha256"])' <<<"$readiness")"
confirmation="INSTALL CANARY $version $sha256"

if [[ -z "${CANARY_INSTALL_CONFIRM:-}" && -t 0 ]]; then
  printf 'Type exactly: %s\n> ' "$confirmation" >&2
  IFS= read -r CANARY_INSTALL_CONFIRM
fi
if [[ "${CANARY_INSTALL_CONFIRM:-}" != "$confirmation" ]]; then
  echo "Canary installation confirmation is missing or does not match." >&2
  exit 1
fi

readiness="$(${PYTHON:-python3} "$SCRIPT_DIR/check_canary_deploy_readiness.py" \
  "$FIRMWARE" "$MANIFEST" "$ENDURANCE_SUMMARY" \
  --expected-firmware-sha256 "$EXPECTED_SHA256" --format json)"
[[ "$(${PYTHON:-python3} -c 'import json,sys; print(json.load(sys.stdin)["sha256"])' \
  <<<"$readiness")" == "$sha256" ]] || {
  echo "Canary candidate changed after confirmation." >&2
  exit 1
}

firmware_abs="$(${PYTHON:-python3} -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$FIRMWARE")"
ota_secrets_abs="$(${PYTHON:-python3} -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$OTA_SECRETS")"

docker run --rm \
  -v "$firmware_abs:/candidate/firmware.ota.bin:ro" \
  -v "$ota_secrets_abs:/run/secrets/muse.yaml:ro" \
  -v "$SCRIPT_DIR/upload_exact_ota.py:/tool/upload_exact_ota.py:ro" \
  --entrypoint python "$IMAGE" /tool/upload_exact_ota.py \
  --host "$DEVICE_HOST" --artifact /candidate/firmware.ota.bin \
  --expected-sha256 "$sha256" \
  --secrets /run/secrets/muse.yaml

${PYTHON:-python3} "$SCRIPT_DIR/verify_canary_boot.py" \
  --host "$DEVICE_HOST" --expected-version "$version" --secrets "$VERIFY_SECRETS"

echo "Installed and verified exact canary version=$version sha256=$sha256."
