#!/usr/bin/env bash
set -euo pipefail

usage="Usage: rollback_hal6_ota.sh HAL6_ARTIFACT SHA256 HOST"
FIRMWARE="${1:?$usage}"
EXPECTED_SHA256="${2:?$usage}"
DEVICE_HOST="${3:?$usage}"
SECRETS="${SECRETS:-secrets.yaml}"
HAL6_REFERENCE_SECRETS="${HAL6_REFERENCE_SECRETS:-}"
IMAGE="esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$SECRETS" ]]; then
  echo "Secrets file not found: $SECRETS" >&2
  exit 1
fi
if [[ -z "$HAL6_REFERENCE_SECRETS" || ! -f "$HAL6_REFERENCE_SECRETS" ]]; then
  echo "Set HAL6_REFERENCE_SECRETS to the private immutable hal.6 credential reference." >&2
  echo "The public example file is never accepted; use USB recovery when unavailable." >&2
  exit 1
fi
version="$(${PYTHON:-python3} "$SCRIPT_DIR/check_rollback_artifact.py" "$FIRMWARE" \
  --manifest "$ROOT/manifest_update.json" --expected-sha256 "$EXPECTED_SHA256")"
${PYTHON:-python3} "$SCRIPT_DIR/check_hal6_credential_compatibility.py" \
  "$SECRETS" "$HAL6_REFERENCE_SECRETS" >/dev/null
confirmation="ROLLBACK $version $EXPECTED_SHA256"
if [[ -z "${ROLLBACK_CONFIRM:-}" && -t 0 ]]; then
  printf 'Type exactly: %s\n> ' "$confirmation" >&2
  IFS= read -r ROLLBACK_CONFIRM
fi
if [[ "${ROLLBACK_CONFIRM:-}" != "$confirmation" ]]; then
  echo "Rollback confirmation is missing or does not match." >&2
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
echo "Rollback installed and verified version=$version sha256=$EXPECTED_SHA256."
