#!/usr/bin/env bash
set -euo pipefail

usage="Usage: install_canary_ota.sh ARTIFACT MANIFEST ENDURANCE_SUMMARY SHA256 HOST"
FIRMWARE="${1:?$usage}"
MANIFEST="${2:?$usage}"
ENDURANCE_SUMMARY="${3:?$usage}"
EXPECTED_SHA256="${4:?$usage}"
DEVICE_HOST="${5:?$usage}"
SECRETS="${SECRETS:-secrets.yaml}"
IMAGE="esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "Refusing canary installation from a dirty worktree." >&2
  exit 1
fi
if [[ ! -f "$SECRETS" ]]; then
  echo "Secrets file not found: $SECRETS" >&2
  exit 1
fi

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

firmware_abs="$(${PYTHON:-python3} -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$FIRMWARE")"
secrets_abs="$(${PYTHON:-python3} -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$SECRETS")"

docker run --rm \
  -v "$firmware_abs:/candidate/firmware.ota.bin:ro" \
  -v "$secrets_abs:/run/secrets/muse.yaml:ro" \
  -v "$SCRIPT_DIR/upload_exact_ota.py:/tool/upload_exact_ota.py:ro" \
  --entrypoint python "$IMAGE" /tool/upload_exact_ota.py \
  --host "$DEVICE_HOST" --artifact /candidate/firmware.ota.bin \
  --secrets /run/secrets/muse.yaml

${PYTHON:-python3} "$SCRIPT_DIR/verify_canary_boot.py" \
  --host "$DEVICE_HOST" --expected-version "$version" --secrets "$SECRETS"

echo "Installed and verified exact canary version=$version sha256=$sha256."
