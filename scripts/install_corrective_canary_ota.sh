#!/usr/bin/env bash
set -euo pipefail

usage="Usage: install_corrective_canary_ota.sh NEW_ARTIFACT MANIFEST BUILD_METADATA INCIDENT RAW_JSONL OLD_ARTIFACT SOURCE_CI NEW_SHA256 OLD_SHA256 HOST"
FIRMWARE="${1:?$usage}"
MANIFEST="${2:?$usage}"
BUILD_METADATA="${3:?$usage}"
INCIDENT="${4:?$usage}"
RAW_JSONL="${5:?$usage}"
OLD_FIRMWARE="${6:?$usage}"
SOURCE_CI="${7:?$usage}"
NEW_SHA256="${8:?$usage}"
OLD_SHA256="${9:?$usage}"
DEVICE_HOST="${10:?$usage}"
SECRETS="${SECRETS:-secrets.yaml}"
OTA_SECRETS="${OTA_SECRETS:-$SECRETS}"
VERIFY_SECRETS="${VERIFY_SECRETS:-$SECRETS}"
IMAGE="esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "Refusing corrective installation from a dirty worktree." >&2
  exit 1
fi
source_commit="$(git -C "$ROOT" rev-parse HEAD)"
for secrets_file in "$OTA_SECRETS" "$VERIFY_SECRETS"; do
  if [[ ! -f "$secrets_file" ]]; then
    echo "Secrets file not found: $secrets_file" >&2
    exit 1
  fi
done

readiness="$(${PYTHON:-python3} "$SCRIPT_DIR/check_corrective_canary_readiness.py" \
  "$FIRMWARE" "$MANIFEST" "$BUILD_METADATA" "$INCIDENT" "$RAW_JSONL" \
  "$OLD_FIRMWARE" "$SOURCE_CI" \
  --new-sha256 "$NEW_SHA256" --old-sha256 "$OLD_SHA256" \
  --source-commit "$source_commit" --format json)"
version="$(${PYTHON:-python3} -c 'import json,sys; print(json.load(sys.stdin)["new_version"])' <<<"$readiness")"
incident_sha="$(${PYTHON:-python3} -c 'import json,sys; print(json.load(sys.stdin)["incident_record_sha256"])' <<<"$readiness")"
confirmation="INSTALL CORRECTIVE CANARY $version $NEW_SHA256 $incident_sha"

if [[ -z "${CORRECTIVE_INSTALL_CONFIRM:-}" && -t 0 ]]; then
  printf 'Type exactly: %s\n> ' "$confirmation" >&2
  IFS= read -r CORRECTIVE_INSTALL_CONFIRM
fi
if [[ "${CORRECTIVE_INSTALL_CONFIRM:-}" != "$confirmation" ]]; then
  echo "Corrective installation confirmation is missing or does not match." >&2
  exit 1
fi

readiness="$(${PYTHON:-python3} "$SCRIPT_DIR/check_corrective_canary_readiness.py" \
  "$FIRMWARE" "$MANIFEST" "$BUILD_METADATA" "$INCIDENT" "$RAW_JSONL" \
  "$OLD_FIRMWARE" "$SOURCE_CI" \
  --new-sha256 "$NEW_SHA256" --old-sha256 "$OLD_SHA256" \
  --source-commit "$source_commit" --format json)"
[[ "$(${PYTHON:-python3} -c 'import json,sys; print(json.load(sys.stdin)["incident_record_sha256"])' \
  <<<"$readiness")" == "$incident_sha" ]] || {
  echo "Corrective evidence changed after confirmation." >&2
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
  --expected-sha256 "$NEW_SHA256" \
  --secrets /run/secrets/muse.yaml

${PYTHON:-python3} "$SCRIPT_DIR/verify_canary_boot.py" \
  --host "$DEVICE_HOST" --expected-version "$version" --secrets "$VERIFY_SECRETS"

echo "Installed and verified exact corrective canary version=$version sha256=$NEW_SHA256."
